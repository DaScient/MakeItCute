# /Users/dontadaya/PrettyPython/projects/MakeItCute/ForNicole/tools/telnet_tutor.py
import sys, subprocess, asyncio

# Ensure telnetlib3 is available (Python 3.13+ replacement for stdlib telnetlib)
try:
    import telnetlib3  # type: ignore
except Exception:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "telnetlib3"])
    import telnetlib3  # type: ignore

HOST, PORT = "telehack.com", 23

async def main():
    try:
        reader, writer = await telnetlib3.open_connection(HOST, PORT, encoding="utf8")
        # ask for help right away
        writer.write("help\n")
        await writer.drain()

        try:
            out = await asyncio.wait_for(reader.read(2000), timeout=1.5)
        except asyncio.TimeoutError:
            out = ""

        if out:
            print("----- Help excerpt -----")
            print(out[:1000])

        writer.write("quit\n")
        await writer.drain()
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        print("Disconnected.")
    except Exception as e:
        print("Error:", e)
        print("Tip: Some networks block outbound telnet (port 23). Try another network or VPN.")

if __name__ == "__main__":
    asyncio.run(main())
