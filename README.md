# 📡 Network File Transfer App

โปรเจกต์นี้เป็น **UDP Client-Server** สำหรับส่งไฟล์แบบ Reliable โดยใช้ **Stop-and-Wait ARQ** และ **Go-Back-N Protocol**

## ✨ Features

- ✅ **GUI แบบง่าย** - ใช้งานง่าย ไม่ต้องพิมพ์คำสั่ง
- ✅ **2 โปรโตคอล** - Stop-and-Wait และ Go-Back-N
- ✅ **จำลอง Packet Loss/Corruption** - ตั้งค่าได้เอง
- ✅ **Real-time Log** - ดู log การส่งข้อมูลแบบ real-time
- ✅ **Progress Bar** - แสดงความคืบหน้าในการส่งไฟล์
- ✅ **รองรับทุกไฟล์** - Text, Image, Binary 

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

### 🎨 วิธีที่ 1: ใช้ GUI (แนะนำ - ง่ายที่สุด!)

#### เปิด Server GUI
```bash
python3 server_gui.py
```
จากนั้น:
1. เลือกโปรโตคอล (Stop-and-Wait หรือ Go-Back-N)
2. ตั้งค่า Port, Loss Rate, Corrupt Rate
3. กดปุ่ม "▶ เริ่ม Server"

#### เปิด Client GUI (ใน terminal ใหม่)
```bash
python3 client_gui.py
```
จากนั้น:
1. เลือกโปรโตคอลเดียวกับ Server
2. ใส่ Server IP และ Port
3. กดปุ่ม "📁 เลือกไฟล์"
4. กดปุ่ม "📤 ส่งไฟล์"

### 💻 วิธีที่ 2: ใช้ Command Line

#### Server (Stop-and-Wait)
```bash
python server.py 5000 --loss 0.1 --corrupt 0.05
```

#### Client (Stop-and-Wait)
```bash
python client.py 127.0.0.1 5000 tests/small.txt
```

#### Server (Go-Back-N)
```bash
python server_gbn.py 5000 --loss 0.05 --corrupt 0.02
```

#### Client (Go-Back-N)
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