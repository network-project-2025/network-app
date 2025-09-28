import struct
import hashlib
from enum import IntEnum

# กำหนดค่าคงที่
PACKET_SIZE = 1024  # ขนาด data สูงสุดต่อ packet
HEADER_SIZE = 9 # ขนาด header ของ packet
TIMEOUT = 1.0       # รอ ACK 1 วินาที เป็นค่ามาตรฐาน
MAX_RETRIES = 5     # ส่งซ้ำสูงสุด 5 ครั้ง

class PacketType(IntEnum): # ประเภทของ packet
    REQUEST = 1     # Client ขอไฟล์จาก Server
    DATA = 2        # Server ส่งข้อมูลไฟล์
    ACK = 3         # Client ตอบรับว่าได้ข้อมูลแล้ว
    EOF = 4         # Server บอกว่าไฟล์จบแล้ว
    ERROR = 5       # แจ้ง error 

class Packet:
    def __init__(self, packet_type, seq_num, data=b''):  # ใช้ตรวจสอบลำดับ, ป้องกัน packet หาย/ซ้ำ
        self.type = packet_type
        self.seq_num = seq_num 
        self.data = data[:PACKET_SIZE]
        self.checksum = 0

    def calculate_checksum(self): # คำนวณ checksum ของ packet
            # สร้าง packet ชั่วคราว (ไม่รวม checksum)
            temp_packet = struct.pack('!BIH', 
                                    self.type, 
                                    self.seq_num, 
                                    len(self.data))
            temp_packet += self.data
            checksum = 0
            # อ่านทีละ 16-bit (2 bytes)
            for i in range(0, len(temp_packet), 2):
                if i + 1 < len(temp_packet):
                    # มี 2 bytes เต็ม
                    word = (temp_packet[i] << 8) + temp_packet[i + 1]
                else:
                    # เหลือ 1 byte สุดท้าย
                    word = temp_packet[i] << 8
                
                checksum += word
                # ถ้ามี carry ให้บวกกลับ
                checksum = (checksum & 0xFFFF) + (checksum >> 16)
            
            # One's complement
            checksum = ~checksum & 0xFFFF
            return checksum
    
    def to_bytes(self): # แปลง packet เป็น bytes สำหรับส่งผ่าน network
        self.checksum = self.calculate_checksum() # คำนวณ checksum ก่อนส่ง
        header = struct.pack('!BIHH',
                             self.type, 
                             self.seq_num, 
                             len(self.data), 
                             self.checksum)
        return header + self.data
    
    @classmethod
    def from_bytes(cls, byte_data): # แปลง bytes ที่รับมาเป็น packet
        if len(byte_data) < HEADER_SIZE:
            return None, False
        packet_type, seq_num, data_len, recv_checksum = struct.unpack('!BIHH', byte_data[:HEADER_SIZE]) 
        if len(byte_data) < HEADER_SIZE + data_len: 
            return None, False 
        data = byte_data[HEADER_SIZE:HEADER_SIZE + data_len] 

        pkt = cls(PacketType(packet_type), seq_num, data)
        calc_checksum = pkt.calculate_checksum()
        if calc_checksum != recv_checksum:
            return None, False

        pkt.checksum = recv_checksum
        return pkt, True

# ฟังก์ชันช่วยสร้าง packet ประเภทต่างๆ
def create_request_packet(filename): # สร้าง packet สำหรับขอไฟล์
    return Packet(PacketType.REQUEST, 0, filename.encode('utf-8'))

def create_data_packet(seq_num, data):  # สร้าง packet สำหรับส่งข้อมูลไฟล์
    return Packet(PacketType.DATA, seq_num, data)

def create_ack_packet(seq_num):  # สร้าง packet สำหรับตอบรับข้อมูล
    return Packet(PacketType.ACK, seq_num)

def create_eof_packet(seq_num, file_hash):  # สร้าง packet สำหรับบอกว่าไฟล์จบแล้ว
    return Packet(PacketType.EOF, seq_num, file_hash)

def create_error_packet(error_msg):  # สร้าง packet สำหรับแจ้ง error
    return Packet(PacketType.ERROR, 0, error_msg.encode('utf-8'))

def calculate_file_hash(data): # คำนวณ MD5 hash ของไฟล์
    return hashlib.md5(data).digest()
    

        