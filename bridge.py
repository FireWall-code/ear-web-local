#!/usr/bin/env python3
import socket
import subprocess
import re
import json
import threading
import sys
import asyncio
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    subprocess.run([sys.executable, "-m", "pip", "install", "websockets"], check=True)
    import websockets

BRIDGE_PORT = 8765
WEB_PORT = 3000
AF_BTH = 32
BTHPROTO_RFCOMM = 3

bt_sock = None
bt_connected = False
ws_clients = set()
event_loop = None
has_had_clients = False

def get_nothing_ear_mac():
    cmd = ('Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue '
           '| Select-Object FriendlyName,InstanceId '
           '| ConvertTo-Json -Compress')
    try:
        result = subprocess.run(
            ['powershell', '-Command', cmd],
            capture_output=True, text=True, errors='ignore', timeout=15
        )
        if not result.stdout.strip():
            return None, None
        data = json.loads(result.stdout)
        if isinstance(data, dict):
            data = [data]
        for device in data:
            name = device.get('FriendlyName', '')
            iid = device.get('InstanceId', '')
            if name and ('Nothing' in name or 'Ear' in name or 'CMF' in name):
                m = re.search(r'DEV_([0-9A-Fa-f]{12})', iid)
                if m:
                    h = m.group(1)
                    mac = ':'.join(h[i:i+2] for i in range(0, 12, 2))
                    return mac, name
    except Exception:
        pass
    return None, None

def try_rfcomm(mac, channel):
    try:
        s = socket.socket(AF_BTH, socket.SOCK_STREAM, BTHPROTO_RFCOMM)
        s.settimeout(2)
        s.connect((mac, channel))
        s.settimeout(None)
        return s
    except Exception:
        return None

def find_rfcomm(mac):
    print(f"\n[*] Searching for RFCOMM channel (trying channels 1-30)...")
    active_channels = []
    for ch in range(1, 31):
        print(f"    -> Channel {ch}...", end=' ', flush=True)
        s = try_rfcomm(mac, ch)
        if s:
            print("OK!")
            active_channels.append((ch, s))
        else:
            print("failed")

    if not active_channels:
        return None, None

    print(f"\n[*] {len(active_channels)} active channel(s) found. Testing Nothing protocol...")
    test_cmd = bytes.fromhex("55600106c0000001911f")

    for ch, s in active_channels:
        print(f"    -> Testing channel {ch}...", end=' ', flush=True)
        try:
            s.settimeout(3.0)
            s.sendall(test_cmd)
            data = s.recv(1024)
            if data and data[0] == 0x55:
                print(f"RESPONSE! ({data.hex()})")
                s.settimeout(None)
                for other_ch, other_s in active_channels:
                    if other_ch != ch:
                        try: other_s.close()
                        except: pass
                return ch, s
            else:
                print("wrong response")
        except Exception:
            print("timeout")

    print("\n[-] No channel responded.")
    for ch, s in active_channels:
        try: s.close()
        except: pass
    return None, None

def broadcast_sync(data):
    global event_loop
    if event_loop and not event_loop.is_closed():
        for ws in list(ws_clients):
            asyncio.run_coroutine_threadsafe(ws.send(data), event_loop)

def bt_reader():
    global bt_sock, bt_connected
    while bt_sock:
        try:
            data = bt_sock.recv(4096)
            if not data:
                break
            print(f"<- {data.hex()}")
            broadcast_sync(data)
        except Exception:
            break
    print("[-] Bluetooth disconnected")
    bt_connected = False
    broadcast_sync(json.dumps({'type': 'disconnected'}))

def shutdown():
    print("\n[*] Shutting down server...")
    if bt_sock:
        try: bt_sock.close()
        except: pass
    os._exit(0)

async def handle_ws(ws):
    global bt_sock, bt_connected, has_had_clients
    ws_clients.add(ws)
    has_had_clients = True
    print("[+] Browser connected")
    await ws.send(json.dumps({'type': 'connected' if bt_connected else 'connecting'}))
    try:
        async for msg in ws:
            if isinstance(msg, bytes) and bt_sock and bt_connected:
                print(f"-> {msg.hex()}")
                try:
                    bt_sock.sendall(msg)
                except Exception as e:
                    print(f"[!] BT send error: {e}")
    except Exception:
        pass
    finally:
        ws_clients.discard(ws)
        print("[-] Browser disconnected")
        if has_had_clients and len(ws_clients) == 0:
            print("[*] Last tab closed, shutting down in 3 seconds...")
            asyncio.get_event_loop().call_later(3, check_and_shutdown)

def check_and_shutdown():
    if len(ws_clients) == 0 and has_had_clients:
        shutdown()

def start_web_server():
    web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'res')
    os.chdir(web_dir)
    handler = SimpleHTTPRequestHandler
    httpd = HTTPServer(('localhost', WEB_PORT), handler)
    print(f"[*] Web server running on http://localhost:{WEB_PORT}")
    httpd.serve_forever()

async def main():
    global bt_sock, bt_connected, event_loop
    event_loop = asyncio.get_event_loop()

    # Start the web server in a thread
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()

    print("=========================================")
    print("           EAR WEB PYTHON BRIDGE         ")
    print("=========================================")
    print("[*] Searching for Nothing/CMF Ear via PowerShell...")
    
    mac, name = get_nothing_ear_mac()
    if mac:
        print(f"[+] Found Device: {name}")
        print(f"    MAC Address:  {mac}")
    else:
        print("[-] Not found automatically.")
        mac = input("[?] Enter MAC address (e.g., AB:CD:EF:12:34:56): ").strip()

    if mac:
        ch, bt_sock = find_rfcomm(mac)
        if bt_sock:
            bt_connected = True
            print(f"\n[+] Connected successfully!")
            print(f"    RFCOMM Channel: {ch}")
            
            # Launch the browser automatically on success
            print("\n[*] Opening browser in App Mode...")
            subprocess.run(["start", "msedge", "--app=http://localhost:3000"], shell=True)
            
            threading.Thread(target=bt_reader, daemon=True).start()
        else:
            print("\n[-] Could not find the correct Bluetooth channel.")
            print("    \nPlease ensure your device is paired and in range.")
            input("\nPress Enter to exit...")
            sys.exit(1)
    else:
        print("\n[-] No MAC address provided. Exiting...")
        sys.exit(1)

    print("\n=========================================")
    print("          >>> SERVER READY <<<           ")
    print("    WebSocket running on ws://localhost:8765")
    print("=========================================\n")

    async with websockets.serve(handle_ws, "localhost", BRIDGE_PORT):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
