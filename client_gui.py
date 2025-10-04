#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import threading
import subprocess
import sys
import os

class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("UDP File Transfer Client")
        self.root.geometry("700x650")
        self.client_process = None
        self.selected_file = None

        # สร้าง UI
        self.create_widgets()

    def create_widgets(self):
        # Frame สำหรับการตั้งค่า
        config_frame = ttk.LabelFrame(self.root, text="การตั้งค่า Client", padding=10)
        config_frame.pack(fill="x", padx=10, pady=10)

        # Protocol
        ttk.Label(config_frame, text="โปรโตคอล:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.protocol_var = tk.StringVar(value="Go-Back-N")
        protocol_combo = ttk.Combobox(config_frame, textvariable=self.protocol_var,
                                      values=["Stop-and-Wait", "Go-Back-N"], state="readonly", width=20)
        protocol_combo.grid(row=0, column=1, padx=5, pady=5)

        # Server IP
        ttk.Label(config_frame, text="Server IP:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(config_frame, textvariable=self.ip_var, width=20).grid(row=1, column=1, padx=5, pady=5)

        # Port
        ttk.Label(config_frame, text="Port:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.port_var = tk.StringVar(value="5000")
        ttk.Entry(config_frame, textvariable=self.port_var, width=10).grid(row=1, column=3, padx=5, pady=5)

        # ไฟล์ที่จะส่ง
        file_frame = ttk.LabelFrame(self.root, text="เลือกไฟล์", padding=10)
        file_frame.pack(fill="x", padx=10, pady=10)

        self.file_label = ttk.Label(file_frame, text="ยังไม่ได้เลือกไฟล์", foreground="gray")
        self.file_label.pack(side="left", padx=5)

        ttk.Button(file_frame, text="📁 เลือกไฟล์", command=self.select_file).pack(side="right", padx=5)

        # ปุ่ม Send
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.send_btn = ttk.Button(button_frame, text="📤 ส่งไฟล์", command=self.send_file, state="disabled")
        self.send_btn.pack(side="left", padx=5)

        self.clear_btn = ttk.Button(button_frame, text="🗑 ล้าง Log", command=self.clear_log)
        self.clear_btn.pack(side="left", padx=5)

        # Progress Bar
        progress_frame = ttk.LabelFrame(self.root, text="ความคืบหน้า", padding=5)
        progress_frame.pack(fill="x", padx=10, pady=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, mode='determinate')
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        self.status_label = ttk.Label(progress_frame, text="พร้อมส่งไฟล์", foreground="gray")
        self.status_label.pack(padx=5, pady=2)

        # Log
        log_frame = ttk.LabelFrame(self.root, text="Client Log", padding=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state="disabled",
                                                   bg="#1e1e1e", fg="#00ff00",
                                                   font=("Courier New", 9))
        self.log_text.pack(fill="both", expand=True)

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")

    def select_file(self):
        filename = filedialog.askopenfilename(
            title="เลือกไฟล์ที่ต้องการส่ง",
            initialdir="./tests",
            filetypes=[
                ("All files", "*.*"),
                ("Text files", "*.txt"),
                ("Image files", "*.jpg *.png *.gif")
            ]
        )
        if filename:
            self.selected_file = filename
            self.file_label.config(text=os.path.basename(filename), foreground="blue")
            self.send_btn.config(state="normal")
            self.log(f"✅ เลือกไฟล์: {filename}")

    def send_file(self):
        if not self.selected_file:
            self.log("❌ กรุณาเลือกไฟล์ก่อน")
            return

        try:
            ip = self.ip_var.get()
            port = int(self.port_var.get())

            # เลือกไฟล์ client ตาม protocol
            if self.protocol_var.get() == "Stop-and-Wait":
                client_file = "client.py"
            else:
                client_file = "client_gbn.py"

            # สร้างคำสั่ง
            cmd = [sys.executable, client_file, ip, str(port), self.selected_file]

            self.log(f"═══════════════════════════════════════")
            self.log(f"เริ่มส่งไฟล์ด้วย {self.protocol_var.get()}")
            self.log(f"Server: {ip}:{port}")
            self.log(f"ไฟล์: {os.path.basename(self.selected_file)}")
            self.log(f"═══════════════════════════════════════")

            # ปิดปุ่ม
            self.send_btn.config(state="disabled")
            self.status_label.config(text="กำลังส่งไฟล์...", foreground="orange")
            self.progress_var.set(0)

            # เริ่ม client process
            self.client_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # เริ่ม thread สำหรับอ่าน output
            threading.Thread(target=self.read_output, daemon=True).start()

        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาด: {str(e)}")
            self.status_label.config(text="เกิดข้อผิดพลาด", foreground="red")
            self.send_btn.config(state="normal")

    def read_output(self):
        packet_count = 0
        total_packets = 0

        while self.client_process and self.client_process.poll() is None:
            # อ่าน stdout
            line = self.client_process.stdout.readline()
            if line:
                self.log(line.rstrip())

                # คำนวณ progress จาก log
                if "DATA #" in line or "ACK #" in line:
                    packet_count += 1
                    if total_packets == 0:
                        total_packets = 100  # ประมาณการ
                    progress = min(95, (packet_count / total_packets) * 100)
                    self.progress_var.set(progress)

            # อ่าน stderr
            line = self.client_process.stderr.readline()
            if line:
                self.log(line.rstrip())

        # อ่านข้อมูลที่เหลือ
        if self.client_process:
            out, err = self.client_process.communicate()
            if out:
                for line in out.split('\n'):
                    if line:
                        self.log(line)
            if err:
                for line in err.split('\n'):
                    if line:
                        self.log(line)

        # ตรวจสอบว่าส่งสำเร็จหรือไม่
        success = self.client_process and self.client_process.returncode == 0

        self.root.after(100, lambda: self.on_transfer_complete(success))

    def on_transfer_complete(self, success):
        self.send_btn.config(state="normal")

        if success:
            self.progress_var.set(100)
            self.status_label.config(text="✅ ส่งไฟล์สำเร็จ!", foreground="green")
            self.log("═══════════════════════════════════════")
            self.log("✅ ส่งไฟล์สำเร็จ!")
            self.log("═══════════════════════════════════════")
        else:
            self.status_label.config(text="❌ ส่งไฟล์ไม่สำเร็จ", foreground="red")
            self.log("═══════════════════════════════════════")
            self.log("❌ เกิดข้อผิดพลาดในการส่งไฟล์")
            self.log("═══════════════════════════════════════")

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientGUI(root)
    root.mainloop()
