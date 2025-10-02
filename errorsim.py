import random
import logging

# ตั้งค่า logging 
logging.basicConfig(
    level=logging.WARNING,  # แสดงเฉพาะ WARNING ขึ้นไป
    format='[%(levelname)s] %(message)s'
)

class ErrorSim:
    def __init__(self, loss_rate=0.0, corrupt_rate=0.0, seed=None):  
        # loss_rate : float (0.0-1.0)   ความน่าจะเป็นที่จะ drop packet
        # corrupt_rate : float (0.0-1.0) ความน่าจะเป็นที่จะ corrupt packet
        # seed : int (optional)         เพื่อให้สุ่มเหมือนเดิมทุกครั้ง (debug/test)
    
        self.loss_rate = max(0.0, min(1.0, loss_rate))
        self.corrupt_rate = max(0.0, min(1.0, corrupt_rate))
        self.rnd = random.Random(seed)
        
        # เพิ่มสถิติ 
        self.total_packets = 0
        self.dropped_packets = 0
        self.corrupted_packets = 0
    
    def process(self, packet_bytes, seq_num=None):
        # จำลองการส่ง packet ผ่านเครือข่ายที่มีการสูญหาย/เสียหาย
        self.total_packets += 1
        
        # Drop packet
        if self.rnd.random() < self.loss_rate:
            self.dropped_packets += 1
            # Log เฉพาะเมื่อมี seq_num 
            if seq_num is not None:
                logging.warning(f"DROPPED packet #{seq_num}")
            return None
        
        # Corrupt packet
        if self.rnd.random() < self.corrupt_rate and packet_bytes:
            self.corrupted_packets += 1
            if seq_num is not None:
                logging.warning(f"CORRUPTED packet #{seq_num}")
            
            # Corruption หลายแบบ 
            corruption_type = self.rnd.randint(1, 3)
            b = bytearray(packet_bytes)
            
            if corruption_type == 1:
                # Flip single byte 
                i = self.rnd.randrange(len(b))
                b[i] ^= 0xFF
            elif corruption_type == 2:
                # Flip random bits in byte
                i = self.rnd.randrange(len(b))
                b[i] ^= self.rnd.randint(1, 255)
            else:
                # Corrupt 2-3 bytes (severe corruption)
                for _ in range(self.rnd.randint(2, min(3, len(b)))):
                    i = self.rnd.randrange(len(b))
                    b[i] ^= self.rnd.randint(1, 255)
            
            return bytes(b)
        
        return packet_bytes
    
    def get_stats(self):
        # คืนค่าสถิติสำหรับแสดงผล
        if self.total_packets == 0:
            return {
                'total': 0,
                'dropped': 0,
                'corrupted': 0,
                'success': 0,
                'drop_rate': 0,
                'corrupt_rate': 0
            }
        
        return {
            'total': self.total_packets,
            'dropped': self.dropped_packets,
            'corrupted': self.corrupted_packets,
            'success': self.total_packets - self.dropped_packets - self.corrupted_packets,
            'drop_rate': self.dropped_packets / self.total_packets,
            'corrupt_rate': self.corrupted_packets / self.total_packets
        }
    
    def print_stats(self): 
        # พิมพ์สถิติการจำลอง error
        stats = self.get_stats()
        print(f"\n=== Error Simulation Stats ===")
        print(f"Total: {stats['total']}")
        print(f"Dropped: {stats['dropped']} ({stats['drop_rate']:.1%})")
        print(f"Corrupted: {stats['corrupted']} ({stats['corrupt_rate']:.1%})")
        print(f"Success: {stats['success']}")
        print("="*30)
    
    def reset_stats(self):
        # รีเซ็ตสถิติทั้งหมด
        self.total_packets = 0
        self.dropped_packets = 0
        self.corrupted_packets = 0