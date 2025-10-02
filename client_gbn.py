import argparse
import socket
import sys
import os
import time
from proto import (
    MAX_PACKET_SIZE, Packet, PacketType,
    create_request_packet, create_ack_packet
)

class GBNClient:
    def __init__(self, server_ip, server_port, timeout=1.0):
        self.server = (server_ip, server_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(timeout)

        # สถิติ
        self.start_time = None
        self.recv_packets = 0
        self.dup_packets = 0
        self.corrupted = 0

    def request(self, filename, save_as=None):
        if save_as is None:
            save_as = f"recv_{os.path.basename(filename)}"

        print(f"[CLIENT-GBN] Request '{filename}' -> {self.server}")
        req = create_request_packet(filename)
        self.sock.sendto(req.to_bytes(), self.server)

        ok = self._receive_gbn(filename, save_as)
        self.sock.close()

        if ok:
            print(f"[CLIENT-GBN] Done. Saved as '{save_as}'")
            return 0
        else:
            if os.path.exists(save_as):
                os.remove(save_as)
            print("[CLIENT-GBN] Failed.")
            return 1

    def _receive_gbn(self, filename, save_as):
        expected = 0            # ลำดับที่คาดว่าจะได้รับ "ตัวถัดไป"
        received = {}           # เก็บเฉพาะ in-order ที่จะเขียน (สามารถเขียนทันทีได้)
        self.start_time = time.time()

        with open(save_as, "wb") as out:
            while True:
                try:
                    data, addr = self.sock.recvfrom(MAX_PACKET_SIZE)
                except socket.timeout:
                    # หากยังไม่เริ่มรับอะไรเลย ให้รอต่อ (server จะส่งซ้ำเอง)
                    if expected == 0:
                        print("[CLIENT-GBN] Waiting for first DATA...")
                        continue
                    # เริ่มรับไปแล้ว แต่เงียบ → อาจรอ EOF หรือ data resend
                    # รอต่อไปตาม timeout วน loop
                    continue

                if addr != self.server:
                    continue

                # แปลงและตรวจ checksum
                pkt, ok = Packet.from_bytes(data)
                if not ok:
                    self.corrupted += 1
                    # ไม่ส่ง ACK สำหรับแพ็กเก็ตเสียหาย
                    continue

                # จัดการชนิดแพ็กเก็ต
                if pkt.type == PacketType.ERROR:
                    msg = pkt.data.decode('utf-8', errors='ignore')
                    print(f"[CLIENT-GBN] Server error: {msg}")
                    return False

                elif pkt.type == PacketType.DATA:
                    self.recv_packets += 1
                    seq = pkt.seq_num

                    if seq == expected:
                        # ถูกลำดับ → เขียนลงไฟล์ แล้วเลื่อน expected
                        out.write(pkt.data)
                        expected += 1
                        # cumulative ACK สำหรับแพ็กเก็ตล่าสุดที่รับครบต่อเนื่อง
                        ack = create_ack_packet(expected - 1)
                        self.sock.sendto(ack.to_bytes(), self.server)
                        print(f"[CLIENT-GBN] DATA #{seq} ok, ACK #{expected-1}")
                    elif seq < expected:
                        # ซ้ำ → ส่ง ACK เดิมซ้ำ (cumulative)
                        self.dup_packets += 1
                        ack = create_ack_packet(expected - 1)
                        self.sock.sendto(ack.to_bytes(), self.server)
                        print(f"[CLIENT-GBN] Duplicate #{seq}, re-ACK #{expected-1}")
                    else:
                        # seq > expected (out-of-order) ใน GBN ให้ทิ้งและส่ง ACK ล่าสุด
                        ack = create_ack_packet(expected - 1) if expected > 0 else create_ack_packet(0)
                        self.sock.sendto(ack.to_bytes(), self.server)
                        print(f"[CLIENT-GBN] Out-of-order #{seq}, expect #{expected}, send ACK #{expected-1 if expected>0 else 0}")

                elif pkt.type == PacketType.EOF:
                    # รับ EOF เมื่อและเฉพาะเมื่อรับครบถึง seq ของ EOF (EOF.seq = จำนวนแพ็กเก็ตข้อมูล)
                    if pkt.seq_num == expected:
                        # ส่ง ACK EOF แล้วจบ
                        ack = create_ack_packet(pkt.seq_num)
                        self.sock.sendto(ack.to_bytes(), self.server)
                        print("[CLIENT-GBN] EOF ok, ACK EOF")
                        break
                    else:
                        # ยังมี data ขาด → ขอซ้ำด้วย ACK ล่าสุด
                        ack = create_ack_packet(expected - 1 if expected > 0 else 0)
                        self.sock.sendto(ack.to_bytes(), self.server)
                        print(f"[CLIENT-GBN] EOF early (have {expected}), send ACK #{expected-1 if expected>0 else 0}")

                else:
                    # ไม่รองรับชนิดอื่น
                    continue

        # สถิติ
        dur = time.time() - self.start_time
        print("========== STATS ==========")
        print(f"Received packets : {self.recv_packets}")
        print(f"Duplicates       : {self.dup_packets}")
        print(f"Corrupted        : {self.corrupted}")
        print(f"Elapsed          : {dur:.2f}s")
        return True

def main():
    ap = argparse.ArgumentParser(description="GBN UDP Client") 
    ap.add_argument("server_ip")
    ap.add_argument("server_port", type=int)
    ap.add_argument("filename")
    ap.add_argument("--timeout", type=float, default=1.0)
    ap.add_argument("-o", "--output")
    args = ap.parse_args()
    
    save_as = args.output or f"receive_test_gbn/recv_gbn_{os.path.basename(args.filename)}" 
    c = GBNClient(args.server_ip, args.server_port, timeout=args.timeout)
    try:
        sys.exit(c.request(args.filename, save_as))
    except KeyboardInterrupt:
        print("\n[CLIENT-GBN] Interrupted.")
        sys.exit(1)

if __name__ == "__main__":
    main()