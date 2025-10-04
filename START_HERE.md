# 🚀 วิธีใช้งานแบบง่ายสุด ๆ

## ขั้นตอนที่ 1: เปิด Server

```bash
python3 server_gui.py
```

1. เลือกโปรโตคอล (Go-Back-N แนะนำ)
2. กดปุ่ม **▶ เริ่ม Server**

---

## ขั้นตอนที่ 2: เปิด Client (เปิด terminal ใหม่)

```bash
python3 client_gui.py
```

1. เลือกโปรโตคอลเดียวกับ Server
2. กดปุ่ม **📁 เลือกไฟล์** (เลือกไฟล์จากโฟลเดอร์ `tests/`)
3. กดปุ่ม **📤 ส่งไฟล์**

---

## เสร็จแล้ว! 🎉

ดู log การส่งข้อมูลใน GUI ทั้ง Server และ Client

### ไฟล์ทดสอบที่แนะนำ:
- `tests/small.txt` - ไฟล์เล็ก
- `tests/large.txt` - ไฟล์ใหญ่
- `tests/image.jpg` - รูปภาพ

### ตรวจสอบผลลัพธ์:
```bash
# เปรียบเทียบไฟล์ต้นฉบับกับไฟล์ที่รับมา
diff tests/large.txt recv_large.txt

# สำหรับไฟล์ binary
cmp tests/image.jpg recv_image.jpg
```
