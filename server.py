import argparse
import os
import socket
import sys
from proto import Packet, PacketType, PACKET_SIZE, TIMEOUT, MAX_RETRIES, create_request_packet, create_data_packet, create_ack_packet, create_eof_packet, create_error_packet
from errorsim import ErrorSim

BUF_SIZE = PACKET_SIZE   # ขนาด buffer สำหรับรับ packet (header + data)
REQUEST_TIMEOUT = 20.0   # ตั้ง timeout สำหรับรอ client ใหม่ 
def main(): 
    parser = argparse.ArgumentParser(description="Reliable UDP Server (Stop-and-Wait)") 
    parser.add_argument("port", type=int, help="UDP port สำหรับรับ request")
    parser.add_argument("--loss", type=float, default=0.0, help="loss rate (0.0-1.0)")
    parser.add_argument("--corrupt", type=float, default=0.0, help="corruption rate (0.0-1.0)")
    args = parser.parse_args()

    # ตั้งค่า error simulator
    sim = ErrorSim(loss_rate=args.loss, corrupt_rate=args.corrupt)

    # สร้าง UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", args.port))
    print(f"[server] Listening on UDP port {args.port} (loss={args.loss:.0%}, corrupt={args.corrupt:.0%})")

    while True:
        try:
            # รอ REQUEST จาก client (timeout 20 วินาที)
            sock.settimeout(REQUEST_TIMEOUT)
            try:
                req_bytes, addr = sock.recvfrom(BUF_SIZE)
            except socket.timeout:
                print("[server] No client request for 20 seconds, shutting down...")
                return
            pkt = Packet.from_bytes(req_bytes)
            if isinstance(pkt, tuple):  # รองรับกรณีคืน (pkt, ok)
                pkt, ok = pkt
                if not ok:
                    continue

            if pkt.type != PacketType.REQUEST:
                continue

            filename = pkt.data.decode("utf-8", errors="ignore")
            print(f"[server] Client {addr} requested file: {filename}")

            if not os.path.exists(filename):
                err = create_error_packet("File not found")
                out = sim.process(err.to_bytes())
                if out is not None:
                    sock.sendto(out, addr)
                print("[server] File not found, sent ERROR")
                continue

            # เริ่มส่งไฟล์
            with open(filename, "rb") as f:
                seq = 0
                while True:
                    chunk = f.read(PACKET_SIZE)
                    if not chunk:
                        # ส่ง EOF
                        eof = create_eof_packet(seq, b"")
                        for _ in range(3):  # ส่งซ้ำกันหล่น
                            out = sim.process(eof.to_bytes(), seq)
                            if out is not None:
                                sock.sendto(out, addr)
                        print(f"[server] Finished sending {filename}")
                        break

                    data_pkt = create_data_packet(seq, chunk)
                    retries = 0
                    while True:
                        # ส่ง DATA packet
                        out = sim.process(data_pkt.to_bytes(), seq)
                        if out is not None:
                            sock.sendto(out, addr)
                        print(f"[server] Sent seq={seq} (len={len(chunk)})")

                        # รอ ACK
                        sock.settimeout(TIMEOUT)
                        got_ack = False
                        try:
                            resp, _ = sock.recvfrom(BUF_SIZE)
                            ack = Packet.from_bytes(resp)
                            if isinstance(ack, tuple):
                                ack, ok = ack
                                if not ok:
                                    continue
                            if ack.type == PacketType.ACK and ack.seq_num == seq:
                                got_ack = True
                        except socket.timeout:
                            got_ack = False

                        if got_ack:
                            print(f"[server] ACK received for seq={seq}")
                            seq += 1
                            break
                        else:
                            retries += 1
                            print(f"[server] Timeout -> Retransmit seq={seq} (retry={retries})")
                            if retries > MAX_RETRIES:
                                print("[server] Too many retries, aborting transfer")
                                return

        except KeyboardInterrupt:
            print("\n[server] Shutting down...")
            sys.exit(0)

if __name__ == "__main__":
    main()