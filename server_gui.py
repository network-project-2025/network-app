#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import subprocess
import os
import signal
import sys

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("UDP File Transfer Server")
        self.root.geometry("700x600")
        self.server_process = None

        # สร้าง UI
        self.create_widgets()

    def create_widgets(self):
        # Frame สำหรับการตั้งค่า
        config_frame = ttk.LabelFrame(self.root, text="การตั้งค่า Server", padding=10)
        config_frame.pack(fill="x", padx=10, pady=10)

        # Protocol
        ttk.Label(config_frame, text="โปรโตคอล:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.protocol_var = tk.StringVar(value="Go-Back-N")
        protocol_combo = ttk.Combobox(config_frame, textvariable=self.protocol_var,
                                      values=["Stop-and-Wait", "Go-Back-N"], state="readonly", width=20)
        protocol_combo.grid(row=0, column=1, padx=5, pady=5)

        # Port
        ttk.Label(config_frame, text="Port:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.port_var = tk.StringVar(value="5000")
        ttk.Entry(config_frame, textvariable=self.port_var, width=10).grid(row=0, column=3, padx=5, pady=5)

        # Loss Rate
        ttk.Label(config_frame, text="Loss Rate (%):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.loss_var = tk.StringVar(value="5")
        ttk.Entry(config_frame, textvariable=self.loss_var, width=10).grid(row=1, column=1, padx=5, pady=5)

        # Corrupt Rate
        ttk.Label(config_frame, text="Corrupt Rate (%):").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.corrupt_var = tk.StringVar(value="2")
        ttk.Entry(config_frame, textvariable=self.corrupt_var, width=10).grid(row=1, column=3, padx=5, pady=5)

        # ปุ่ม Start/Stop
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.start_btn = ttk.Button(button_frame, text="▶ เริ่ม Server", command=self.start_server)
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = ttk.Button(button_frame, text="⏹ หยุด Server", command=self.stop_server, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.clear_btn = ttk.Button(button_frame, text="🗑 ล้าง Log", command=self.clear_log)
        self.clear_btn.pack(side="left", padx=5)

        # สถานะ
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(status_frame, text="สถานะ:").pack(side="left")
        self.status_label = ttk.Label(status_frame, text="ยังไม่ได้เริ่ม", foreground="gray")
        self.status_label.pack(side="left", padx=5)

        # Log
        log_frame = ttk.LabelFrame(self.root, text="Server Log", padding=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, state="disabled",
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

    def start_server(self):
        try:
            port = int(self.port_var.get())
            loss = float(self.loss_var.get()) / 100
            corrupt = float(self.corrupt_var.get()) / 100

            # เลือกไฟล์ server ตาม protocol
            if self.protocol_var.get() == "Stop-and-Wait":
                server_file = "server.py"
            else:
                server_file = "server_gbn.py"

            # สร้างคำสั่ง
            cmd = [sys.executable, server_file, str(port), "--loss", str(loss), "--corrupt", str(corrupt)]

            self.log(f"═══════════════════════════════════════")
            self.log(f"เริ่ม {self.protocol_var.get()} Server")
            self.log(f"Port: {port}")
            self.log(f"Loss Rate: {self.loss_var.get()}%")
            self.log(f"Corrupt Rate: {self.corrupt_var.get()}%")
            self.log(f"═══════════════════════════════════════")

            # เริ่ม server process
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # อัพเดท UI
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.status_label.config(text=f"กำลังทำงาน (Port {port})", foreground="green")

            # เริ่ม thread สำหรับอ่าน output
            threading.Thread(target=self.read_output, daemon=True).start()

        except Exception as e:
            self.log(f"❌ เกิดข้อผิดพลาด: {str(e)}")
            self.status_label.config(text="เกิดข้อผิดพลาด", foreground="red")

    def read_output(self):
        while self.server_process and self.server_process.poll() is None:
            # อ่าน stdout
            line = self.server_process.stdout.readline()
            if line:
                self.log(line.rstrip())

            # อ่าน stderr
            line = self.server_process.stderr.readline()
            if line:
                self.log(line.rstrip())

        # อ่านข้อมูลที่เหลือ
        if self.server_process:
            out, err = self.server_process.communicate()
            if out:
                for line in out.split('\n'):
                    if line:
                        self.log(line)
            if err:
                for line in err.split('\n'):
                    if line:
                        self.log(line)

        self.root.after(100, self.on_server_stopped)

    def on_server_stopped(self):
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="หยุดทำงาน", foreground="gray")
        self.log("═══════════════════════════════════════")
        self.log("Server หยุดทำงานแล้ว")
        self.log("═══════════════════════════════════════")

    def stop_server(self):
        if self.server_process:
            self.log("กำลังหยุด Server...")
            try:
                if sys.platform == 'win32':
                    self.server_process.terminate()
                else:
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
            except:
                self.server_process.kill()
            self.server_process = None

    def on_closing(self):
        self.stop_server()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
