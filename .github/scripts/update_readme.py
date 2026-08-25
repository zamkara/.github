#!/usr/bin/env python3
import os
import sys
import json
import time
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATS_FILE = REPO_ROOT / ".github" / "stats.json"
README_FILE = REPO_ROOT / "README.md"

START_TIME = time.time()

def get_kernel():
    try:
        return platform.release().strip()
    except Exception:
        return "unknown"

def get_packages():
    # Try pacman first (if Arch), then dpkg (Ubuntu runner), then rpm
    try:
        res = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True, check=True)
        return len(res.stdout.strip().splitlines())
    except Exception:
        pass

    try:
        res = subprocess.run(["dpkg-query", "-f", ".\\n", "-W"], capture_output=True, text=True, check=True)
        return len(res.stdout.strip().splitlines())
    except Exception:
        pass

    try:
        res = subprocess.run(["rpm", "-qa"], capture_output=True, text=True, check=True)
        return len(res.stdout.strip().splitlines())
    except Exception:
        pass

    return 0

def get_memory():
    # Read /proc/meminfo in MB
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    meminfo[key] = int(val) # in kB

        total_mb = meminfo.get("MemTotal", 0) // 1024
        avail_mb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0)) // 1024
        used_mb = total_mb - avail_mb
        return f"{used_mb}M / {total_mb}M"
    except Exception:
        return "0M / 0M"

def load_stats():
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"total_seconds": 0, "runs_count": 0, "last_run": None}

def save_stats(stats):
    STATS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2)

def format_uptime(total_seconds):
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"

def update_readme():
    stats = load_stats()
    
    # Calculate elapsed runner time (at least 15s per run to reflect runner execution overhead)
    elapsed = max(int(time.time() - START_TIME), 15)
    stats["total_seconds"] = stats.get("total_seconds", 0) + elapsed
    stats["runs_count"] = stats.get("runs_count", 0) + 1
    stats["last_run"] = datetime.now(timezone.utc).isoformat()
    
    save_stats(stats)
    
    user = "zam@kara"
    os_name = "Arch Linux"
    host_name = "ASUS TUF Gaming F15 FX506LH_FX506LH 1.0"
    kernel_name = get_kernel()
    uptime_str = format_uptime(stats["total_seconds"])
    pkgs_count = get_packages()
    memory_str = get_memory()

    content = f"""```
       /\\         {user}
      /  \\        os     {os_name}
     /\\   \\       host   {host_name}
    /      \\      kernel {kernel_name}
   /   ,,   \\     uptime {uptime_str}
  /   |  |  -\\    pkgs   {pkgs_count}
 /_-''    ''-_\\   memory {memory_str}
```
"""
    with open(README_FILE, "w") as f:
        f.write(content)

    print("README.md updated successfully:")
    print(content)

if __name__ == "__main__":
    update_readme()
