# network-app
# Network File Transfer App

โปรเจกต์นี้เป็น UDP Client-Server สำหรับส่งไฟล์แบบ Reliable โดยใช้ Stop-and-Wait ARQ และ Go-Back-N 

## Installation

```bash
git clone https://github.com/yourusername/network-app.git
cd network-app

# สร้าง virtual environment
python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# หรือ
.\.venv\Scripts\activate    # Windows
```

> โปรเจกต์นี้ใช้แต่ Python built-in libraries ไม่ต้องติดตั้ง dependencies เพิ่ม

## Usage

### Server (Stop-and-Wait)
```bash
python server.py 5000 --loss 0.1 --corrupt 0.05
```

### Client (Stop-and-Wait)
```bash
python client.py 127.0.0.1 5000 tests/small.txt
```

### Server (Go-Back-N)
```bash
python server_gbn.py 5000 --loss 0.05 --corrupt 0.02
```

### Client (Go-Back-N)
```bash
python client_gbn.py 127.0.0.1 5000 tests/large.txt
```

## Test Files
- `tests/small.txt` สำหรับทดสอบข้อความสั้น
- `tests/medium.txt` สำหรับทดสอบข้อความขนาดกลาง
- `tests/large.txt` สำหรับทดสอบไฟล์ขนาดใหญ่
- `tests/image.jpg` สำหรับทดสอบไฟล์ binary

ตรวจสอบผลลัพธ์ด้วย `diff` หรือ `cmp`:
```bash
diff tests/small.txt recv_small.txt
cmp tests/image.jpg recv_image.jpg
```