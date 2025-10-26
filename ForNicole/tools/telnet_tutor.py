"""
telnet_tutor.py — gentle Telnet demonstration.
Educational use only — no live system access.
"""

import telnetlib
import time

HOST = "telehack.com"  # a public sandboxed telnet playground

def connect_demo():
    print("🌐 Connecting to Telehack (a safe retro sandbox)...")
    tn = telnetlib.Telnet(HOST)
    time.sleep(1)
    banner = tn.read_until(b":", timeout=5).decode(errors="ignore")
    print("Server says:\n", banner.strip())
    tn.write(b"help\n")
    time.sleep(1)
    data = tn.read_very_eager().decode(errors="ignore")
    print("----- Help excerpt -----")
    print("\n".join(data.splitlines()[:20]))
    tn.write(b"quit\n")
    tn.close()
    print("Disconnected gracefully.")

if __name__ == "__main__":
    try:
        connect_demo()
    except Exception as e:
        print("❌ Connection error:", e)
