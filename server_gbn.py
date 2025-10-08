import socket
import sys
import os
import time
import logging
from proto import (
    PACKET_SIZE, MAX_PACKET_SIZE, TIMEOUT, MAX_RETRIES,
    Packet, PacketType,
    create_data_packet, create_eof_packet, create_error_packet
)
from errorsim import ErrorSim

logging.basicConfig(level=logging.INFO, format='[SERVER-GBN] %(message)s')

WINDOW_SIZE = 4   # ขนาดหน้าต่าง GBN (ปรับได้ตามเหมาะสม)

class GBNServer:
    def __init__(self, port, loss_rate=0.0, corrupt_rate=0.0):
        self.port = port
        self.sock = None
        self.sim = ErrorSim(loss_rate, corrupt_rate)

        # สถิติ
        self.retx = 0
        self.start_time = None

    def start(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(('', self.port))
            print(f"[server] Listening on UDP port {self.port} (loss={self.sim.loss_rate:.0%}, corrupt={self.sim.corrupt_rate:.0%})")

            while True:
                try:
                    # รอ REQUEST จาก client (timeout 60 วินาที)
                    self.sock.settimeout(60.0)
                    self.handle_once()
                except socket.timeout:
                    print("[server] No client request for 60 seconds, shutting down...")
                    return
                except KeyboardInterrupt:
                    break
        finally:
            if self.sock:
                self.sock.close()

    def handle_once(self):
        # รับ REQUEST
        data, client = self.sock.recvfrom(MAX_PACKET_SIZE)
        pkt, ok = Packet.from_bytes(data)
        if not ok or pkt.type != PacketType.REQUEST:
            logging.info('Ignore non-REQUEST')
            return

        filename = pkt.data.decode('utf-8', errors='ignore')
        logging.info(f"Request '{filename}' from {client}")

        if not os.path.exists(filename):
            self._send_error(client, f'File not found: {filename}')
            return

        # อ่านข้อมูลและสร้างแพ็กเก็ตทั้งหมดล่วงหน้า
        with open(filename, 'rb') as f:
            file_data = f.read()
        total = len(file_data)
        num_packets = (total + PACKET_SIZE - 1) // PACKET_SIZE
        logging.info(f"Size={total} bytes, packets={num_packets}")

        packets = []
        for i in range(num_packets):
            off = i * PACKET_SIZE
            chunk = file_data[off: off + PACKET_SIZE]
            packets.append(create_data_packet(i, chunk))

        # ส่งด้วย GBN
        self._send_gbn(client, packets)

        # ส่ง EOF (seq = จำนวนแพ็กเก็ตข้อมูล)
        eof = create_eof_packet(num_packets, b'')
        self._send_stop_and_wait(client, eof, num_packets)

    def _send_gbn(self, client, packets):
        base = 0
        next_seq = 0
        n = len(packets)

        # ตัวจับเวลาแบบ window-level
        timer_running = False
        timer_start = 0.0

        # ตั้งค่า recv timeout สำหรับรอ ACK
        self.sock.settimeout(TIMEOUT)

        # รีเซ็ตสถิติ
        self.retx = 0
        self.start_time = time.time()

        # ส่งจนกว่าจะ ACK ครบทุกตัว (base เคลื่อนไปถึง n)
        while base < n:
            # ส่งได้เมื่อยังไม่เต็มหน้าต่าง
            while next_seq < base + WINDOW_SIZE and next_seq < n:
                raw = packets[next_seq].to_bytes()
                simd = self.sim.process(raw, next_seq)
                if simd is not None:
                    self.sock.sendto(simd, client)
                    logging.info(f"Send DATA #{next_seq} (window {base}..{base+WINDOW_SIZE-1})")
                else:
                    logging.info(f"Drop DATA #{next_seq} (simulated)")

                # เริ่มจับเวลาเมื่อส่งแพ็กเก็ตแรกในหน้าต่าง
                if not timer_running and base < next_seq + 1:
                    timer_running = True
                    timer_start = time.time()

                next_seq += 1

            # พยายามรับ ACK
            try:
                ack_bytes, addr = self.sock.recvfrom(MAX_PACKET_SIZE)
                if addr != client:
                    continue
                ack_pkt, ok = Packet.from_bytes(ack_bytes)
                if not ok or ack_pkt.type != PacketType.ACK:
                    continue

                ackno = ack_pkt.seq_num  # cumulative ACK ถึงแพ็กเก็ตหมายเลขนี้
                if ackno >= base:
                    base = ackno + 1
                    logging.info(f"ACK up to #{ackno}, slide base -> {base}")
                    # ถ้าเลื่อน base ไปถึง next_seq แสดงว่าไม่มี outstanding packet 
                    if base == next_seq:
                        timer_running = False
                    else:
                        # ยังมี outstanding → รีสตาร์ทนาฬิกา
                        timer_running = True
                        timer_start = time.time()
            except socket.timeout:
                pass

            # ตรวจ timeout window
            if timer_running and (time.time() - timer_start >= TIMEOUT):
                # ส่งซ้ำตั้งแต่ base ถึง next_seq-1
                logging.info(f"Timeout window -> retransmit from #{base} to #{next_seq-1}")
                for s in range(base, next_seq):
                    raw = packets[s].to_bytes()
                    simd = self.sim.process(raw, s)
                    if simd is not None:
                        self.sock.sendto(simd, client)
                    self.retx += 1
                # รีสตาร์ทนาฬิกาใหม่
                timer_start = time.time()

        # สรุปสถิติ
        duration = time.time() - self.start_time
        kbps = (sum(len(p.data) for p in packets) / duration) / 1024 if duration > 0 else 0
        logging.info("All data packets ACKed.")
        logging.info(f"Retransmissions: {self.retx}")
        logging.info(f"Throughput: {kbps:.2f} KB/s")

    def _send_stop_and_wait(self, client, pkt, seq):
        """ส่ง EOF แบบ Stop-and-Wait ให้แน่ใจว่าอีกฝั่งได้รับแน่นอน"""
        raw = pkt.to_bytes()
        for attempt in range(MAX_RETRIES):
            simd = self.sim.process(raw, seq)
            if simd is not None:
                self.sock.sendto(simd, client)
            try:
                self.sock.settimeout(TIMEOUT)
                ack_bytes, addr = self.sock.recvfrom(MAX_PACKET_SIZE)
                if addr != client:
                    continue
                ack_pkt, ok = Packet.from_bytes(ack_bytes)
                if ok and ack_pkt.type == PacketType.ACK and ack_pkt.seq_num == seq:
                    logging.info("EOF ACKed.")
                    return
            except socket.timeout:
                logging.info(f"EOF timeout, retry {attempt+1}/{MAX_RETRIES}")
        logging.info("EOF failed after retries.")

    def _send_error(self, client, msg):
        ep = create_error_packet(msg)
        self.sock.sendto(ep.to_bytes(), client)
        logging.info(f"Send ERROR: {msg}")

def main():
    import argparse
    ap = argparse.ArgumentParser(description="GBN UDP Server")
    ap.add_argument("port", type=int)
    ap.add_argument("--loss", type=float, default=0.0)
    ap.add_argument("--corrupt", type=float, default=0.0)
    args = ap.parse_args()

    srv = GBNServer(args.port, args.loss, args.corrupt)
    try:
        srv.start()
    except KeyboardInterrupt:
        print("\n[SERVER-GBN] Shutting down...")

if __name__ == "__main__":
    main()