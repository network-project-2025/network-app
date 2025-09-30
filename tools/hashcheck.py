import argparse
import hashlib
import os
import sys

CHUNK = 1024 * 1024  # อ่านทีละ 1MB เพื่อลดการใช้หน่วยความจำ

def compute_hash(path: str, algo: str = "sha256") -> str: 
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Compare file hashes")
    parser.add_argument("file_a", help="ไฟล์ต้นฉบับ")
    parser.add_argument("file_b", help="ไฟล์ที่รับมา")
    parser.add_argument("--algo", default="sha256", choices=hashlib.algorithms_available,
                        help="อัลกอริทึม hash (default: sha256)")
    args = parser.parse_args()

    if not os.path.exists(args.file_a) or not os.path.exists(args.file_b):
        print("ไฟล์ไม่พบ")
        sys.exit(2)

    h1 = compute_hash(args.file_a, args.algo)
    h2 = compute_hash(args.file_b, args.algo)

    print(f"Algorithm : {args.algo}")
    print(f"{args.file_a} : {h1}")
    print(f"{args.file_b} : {h2}")

    if h1 == h2:
        print("Result: MATCH (ไฟล์ตรงกัน)")
        sys.exit(0)
    else:
        print("Result: MISMATCH (ไฟล์ไม่ตรงกัน)")
        sys.exit(1)

if __name__ == "__main__":
    main()