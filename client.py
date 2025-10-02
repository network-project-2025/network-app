import argparse 
import socket 
import sys
import time
import os
from proto import (
    Packet, PacketType, PACKET_SIZE, TIMEOUT, MAX_PACKET_SIZE,
    create_request_packet, create_ack_packet  
)

# ขนาด buffer สำหรับรับ packet (กำหนดตามโปรโตคอล)
BUF_SIZE = MAX_PACKET_SIZE

class FileTransferClient:
    def __init__(self, server_ip, server_port):
        # เก็บ address ของ server
        self.server_addr = (server_ip, server_port)
        self.socket = None

        # ตัวแปรเก็บสถิติ 
        self.start_time = None
        self.total_packets = 0
        self.corrupted_packets = 0
        self.duplicate_packets = 0

    def request_file(self, filename, save_as=None):
        # ส่ง REQUEST ไปยัง server เพื่อขอไฟล์ และรับไฟล์นั้น
        if save_as is None:
            save_as = f"receive_test/recv_{os.path.basename(filename)}"

        print(f"[CLIENT] Requesting file: '{filename}'")
        print(f"[CLIENT] Will save as: '{save_as}'")
        print(f"[CLIENT] Server: {self.server_addr[0]}:{self.server_addr[1]}")
        print("-" * 50)

        try:
            # สร้าง UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(5.0)  # timeout สำหรับ response แรก

            # สร้างและส่ง REQUEST packet
            req = create_request_packet(filename)
            self.socket.sendto(req.to_bytes(), self.server_addr)
            print(f"[CLIENT] Sent REQUEST for '{filename}'")

            # เริ่มรับไฟล์
            success = self.receive_file(save_as)

            if success:
                print(f"\n[CLIENT] File transfer completed successfully!")
                print(f"[CLIENT] Saved as: '{save_as}'")
            else:
                print(f"\n[CLIENT] File transfer failed")
                # ถ้าไฟล์เสียหาย → ลบทิ้ง
                if os.path.exists(save_as):
                    os.remove(save_as)

        except socket.timeout:
            print(f"[CLIENT] Timeout - No response from server")
        except Exception as e:
            print(f"[CLIENT] Error: {e}")
        finally:
            if self.socket:
                self.socket.close()

    def receive_file(self, save_filename):
        # รับไฟล์จาก server ทีละ packet
        received_data = {}
        expected_seq = 0
        file_complete = False
        file_hash_received = None

        # รีเซ็ตสถิติใหม่
        self.start_time = time.time()
        self.total_packets = 0
        self.corrupted_packets = 0
        self.duplicate_packets = 0

        # ใช้นับ timeout ติดกัน (กันกรณี EOF หาย)
        consecutive_timeouts = 0

        print(f"\n[CLIENT] Receiving file...")

        while not file_complete:
            try:
                # รับ packet จาก server
                pkt_bytes, addr = self.socket.recvfrom(BUF_SIZE)
                consecutive_timeouts = 0  # reset timeout counter

                # ถ้า packet มาจากที่อื่น → ทิ้ง
                if addr != self.server_addr:
                    print(f"[CLIENT] Packet from unknown source: {addr}")
                    continue

                # แปลง bytes → Packet และตรวจ checksum
                parsed = Packet.from_bytes(pkt_bytes)
                if isinstance(parsed, tuple):
                    packet, ok = parsed
                    if not ok:
                        self.corrupted_packets += 1
                        print(f"[CLIENT] Corrupted packet (checksum failed)")
                        continue
                else:
                    packet = parsed

                self.total_packets += 1

                #  จัดการ packet แต่ละประเภท 
                if packet.type == PacketType.ERROR:
                    # server แจ้ง error 
                    msg = packet.data.decode('utf-8', errors='ignore')
                    print(f"[CLIENT] Server error: {msg}")
                    return False

                elif packet.type == PacketType.DATA:
                    seq = packet.seq_num
                    if seq == expected_seq:
                        # ได้ packet ที่ถูกต้อง → เก็บข้อมูล + ส่ง ACK
                        received_data[seq] = packet.data
                        print(f"[CLIENT] Received packet #{seq} ({len(packet.data)} bytes)")
                        ack = create_ack_packet(seq)
                        self.socket.sendto(ack.to_bytes(), self.server_addr)
                        print(f"[CLIENT] Sent ACK for #{seq}")
                        expected_seq += 1
                    elif seq < expected_seq:
                        # duplicate packet → ส่ง ACK ซ้ำ
                        self.duplicate_packets += 1
                        print(f"[CLIENT] Duplicate #{seq} (expected #{expected_seq})")
                        dup = create_ack_packet(seq)
                        self.socket.sendto(dup.to_bytes(), self.server_addr)
                        print(f"[CLIENT] Resent ACK for #{seq}")
                    else:
                        # out-of-order (ไม่ควรเกิดใน Stop-and-Wait)
                        print(f"[CLIENT] Out of order: got #{seq}, expected #{expected_seq}")

                elif packet.type == PacketType.EOF:
                    # ได้ EOF → จบการรับไฟล์
                    print(f"[CLIENT] Received EOF")
                    if packet.data:
                        file_hash_received = packet.data
                        print(f"[CLIENT] File hash received")
                    eof_ack = create_ack_packet(packet.seq_num)
                    self.socket.sendto(eof_ack.to_bytes(), self.server_addr)
                    print(f"[CLIENT] Sent ACK for EOF")
                    file_complete = True

                # ปรับ timeout ให้รอต่อหลังจากมีความคืบหน้า
                self.socket.settimeout(3.0)

            except socket.timeout:
                # timeout → อาจรอ EOF อยู่
                consecutive_timeouts += 1
                if len(received_data) == 0:
                    if consecutive_timeouts >= 3:
                        print(f"[CLIENT] Timeout x3 - no data received, abort")
                        return False
                    continue
                else:
                    if consecutive_timeouts >= 3:
                        print(f"[CLIENT] Timeout x3 - assuming transfer complete")
                        file_complete = True
                        break
                    continue

            except Exception as e:
                print(f"[CLIENT] Error receiving packet: {e}")
                return False

        # ประกอบไฟล์จาก packet ที่ได้ 
        if not received_data:
            print(f"[CLIENT] No data received")
            return False

        print(f"\n[CLIENT] Assembling file from {len(received_data)} packets...")
        file_data = b''.join(received_data[i] for i in sorted(received_data))

        # เขียนไฟล์ลง disk
        try:
            with open(save_filename, 'wb') as f:
                f.write(file_data)
            print(f"[CLIENT] File saved: {save_filename} ({len(file_data):,} bytes)")
        except Exception as e:
            print(f"[CLIENT] Error saving file: {e}")
            return False

        # แสดงสถิติการโอนถ่าย
        self.print_statistics(len(file_data))
        return True

    def print_statistics(self, file_size):
        # แสดงสถิติการโอนถ่ายไฟล์
        if self.start_time:
            duration = time.time() - self.start_time
            throughput = (file_size / duration) / 1024 if duration > 0 else 0
            print("\n" + "="*50)
            print("TRANSFER STATISTICS")
            print("="*50)
            print(f"File size:           {file_size:,} bytes")
            print(f"Transfer time:       {duration:.2f} seconds")
            print(f"Throughput:          {throughput:.2f} KB/s")
            print(f"Total packets:       {self.total_packets}")
            print(f"Corrupted packets:   {self.corrupted_packets}")
            print(f"Duplicate packets:   {self.duplicate_packets}")
            if self.total_packets > 0:
                err_rate = ((self.corrupted_packets + self.duplicate_packets) / self.total_packets) * 100
                print(f"Error rate:          {err_rate:.1f}%")
            print("="*50)

def main():
    parser = argparse.ArgumentParser(description="Reliable UDP Client (Stop-and-Wait)")
    parser.add_argument("server_ip")
    parser.add_argument("server_port", type=int)
    parser.add_argument("filename")
    parser.add_argument("-o", "--output")
    args = parser.parse_args()

    client = FileTransferClient(args.server_ip, args.server_port)
    try:
        client.request_file(args.filename, args.output)
    except KeyboardInterrupt:
        print("\n[CLIENT] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"[CLIENT] Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()