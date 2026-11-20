"""
Campus Record Manager - Persistent Tunnel Daemon.
Runs Cloudflare Tunnel (or SSH fallback) to maintain a rock-solid, 24/7 public HTTPS link.
Automatically saves the live URL to public_url.txt and monitors health.
"""

import os
import re
import sys
import time
import subprocess
import threading
import urllib.request

PUBLIC_URL_FILE = "public_url.txt"
CLOUDFLARED_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloudflared.exe")
current_url = None
stop_event = threading.Event()

def keepalive_worker():
    """Pings the local and public endpoints periodically to ensure health."""
    global current_url
    while not stop_event.is_set():
        if current_url:
            try:
                req = urllib.request.Request(
                    current_url + "/api/stats",
                    headers={"User-Agent": "CRM-Keepalive/1.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    _ = response.read()
            except Exception:
                pass
        time.sleep(60)

def run_tunnel():
    """Starts the tunnel daemon with auto-restart."""
    global current_url

    # Start health/keepalive thread
    t = threading.Thread(target=keepalive_worker, daemon=True)
    t.start()

    print("==================================================")
    print(" Campus Record Manager - Tunnel Daemon Starting...")
    print("==================================================")

    use_cloudflared = os.path.exists(CLOUDFLARED_EXE)

    if use_cloudflared:
        print(f"Using Cloudflare Tunnel: {CLOUDFLARED_EXE}")
        cmd = [CLOUDFLARED_EXE, "tunnel", "--url", "http://127.0.0.1:5000"]
        url_regex = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
    else:
        print("Using SSH localhost.run fallback...")
        cmd = [
            "ssh",
            "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=4",
            "-o", "StrictHostKeyChecking=no",
            "-R", "80:127.0.0.1:5000",
            "nokey@localhost.run"
        ]
        url_regex = re.compile(r'https://[a-zA-Z0-9-]+\.lhr\.life')

    while not stop_event.is_set():
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            for line in proc.stdout:
                line_str = line.strip()
                match = url_regex.search(line_str)
                if match:
                    found_url = match.group(0)
                    if "api.trycloudflare.com" in found_url or "api.cloudflare.com" in found_url:
                        continue
                    if found_url != current_url:
                        current_url = found_url
                        with open(PUBLIC_URL_FILE, "w", encoding="utf-8") as f:
                            f.write(current_url + "\n")
                        print("==================================================")
                        print(f" Live Public URL: {current_url}")
                        print(f" Saved to {PUBLIC_URL_FILE}")
                        print("==================================================")
                        sys.stdout.flush()

            proc.wait()
            print("Tunnel connection closed. Reconnecting in 3 seconds...")
            time.sleep(3)
        except Exception as e:
            print(f"Tunnel error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    run_tunnel()
