#!/usr/bin/env python3
import os
import sys
import json
import time
import html
import shutil
import platform
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATS_FILE = REPO_ROOT / ".github" / "stats.json"
README_FILE = REPO_ROOT / "README.md"
SVG_FILE = REPO_ROOT / "neofetch.svg"

START_TIME = time.time()

def get_user_at_host():
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        repo_name = repo.split("/")[-1]
        return f"{repo_name}@github"
    try:
        r = subprocess.run(["git", "config", "--get", "remote.origin.url"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            url = r.stdout.strip()
            repo_name = url.split("/")[-1].replace(".git", "")
            if repo_name:
                return f"{repo_name}@github"
    except Exception:
        pass
    return "zamkara@github"

def get_os_name():
    pretty = None
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        pretty = line.split("=", 1)[1].strip("\"' \n")
                        break
                    elif line.startswith("NAME=") and not pretty:
                        pretty = line.split("=", 1)[1].strip("\"' \n")
        except Exception:
            pass
    if not pretty:
        pretty = "Arch Linux"
    return f"{pretty} [{platform.machine()}]"

def get_kernel():
    # If running locally on Arch with zen kernel
    try:
        rel = platform.release().strip()
        if "zen" in rel:
            return f"{rel} ({platform.machine()})"
    except Exception:
        pass

    # Fetch official latest Arch Linux Zen kernel release
    try:
        url = "https://archlinux.org/packages/extra/x86_64/linux-zen/json/"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (GitHubActions)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            pkgver = data.get("pkgver", "")
            pkgrel = data.get("pkgrel", "")
            if pkgver and pkgrel:
                formatted = pkgver.replace(".zen", "-zen") + f"-{pkgrel}-zen"
                return f"{formatted} ({platform.machine()})"
    except Exception as e:
        print(f"Notice: Failed to fetch Arch Linux API ({e})")

    return f"7.1.9-zen1-2-zen ({platform.machine()})"

def get_packages():
    counts = []
    # pacman
    if shutil.which("pacman"):
        try:
            r = subprocess.run(["pacman", "-Qq"], capture_output=True, text=True)
            if r.returncode == 0:
                c = len(r.stdout.strip().splitlines())
                if c > 0:
                    counts.append(f"{c} (pacman)")
        except Exception:
            pass
    # flatpak
    if shutil.which("flatpak"):
        try:
            r = subprocess.run(["flatpak", "list"], capture_output=True, text=True)
            if r.returncode == 0:
                c = len(r.stdout.strip().splitlines())
                if c > 0:
                    counts.append(f"{c} (flatpak)")
        except Exception:
            pass
    # dpkg
    if shutil.which("dpkg-query"):
        try:
            r = subprocess.run(["dpkg-query", "-f", ".\\n", "-W"], capture_output=True, text=True)
            if r.returncode == 0:
                c = len(r.stdout.strip().splitlines())
                if c > 0:
                    counts.append(f"{c} (dpkg)")
        except Exception:
            pass

    return ", ".join(counts) if counts else "0 packages"

def get_memory():
    try:
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    meminfo[key] = int(val)

        total_mb = meminfo.get("MemTotal", 0) // 1024
        avail_mb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0)) // 1024
        used_mb = total_mb - avail_mb
        pct = (used_mb / total_mb * 100) if total_mb > 0 else 0
        return f"{used_mb}MiB / {total_mb}MiB ({pct:.1f}%)"
    except Exception:
        return "0MiB / 0MiB (0%)"

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

def format_uptime(total_seconds, runs_count):
    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0 or days > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0 or days > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")

    time_str = " ".join(parts)
    return f"{time_str} ({runs_count} runs)"

def generate_neofetch_svg(user_header, os_name, host_name, kernel_name, uptime_str, pkgs_count, memory_str):
    logo_lines = [
        r"       /\         ",
        r"      /  \        ",
        r"     /\   \       ",
        r"    /      \      ",
        r"   /   ,,   \     ",
        r"  /   |  |  -\    ",
        r" /_-''    ''-_\   ",
    ]

    info_rows = [
        ("", user_header, True),
        ("os        ", os_name, False),
        ("host      ", host_name, False),
        ("kernel    ", kernel_name, False),
        ("uptime    ", uptime_str, False),
        ("pkgs      ", pkgs_count, False),
        ("memory    ", memory_str, False),
    ]

    fontSize = 13
    lineHeight = 21
    paddingY = 12
    paddingX = 8

    max_line_len = 0
    for i in range(len(logo_lines)):
        title, val, is_header = info_rows[i]
        line_str = logo_lines[i] + title + val
        if len(line_str) > max_line_len:
            max_line_len = len(line_str)

    charWidth = 7.8
    width = int(max_line_len * charWidth) + paddingX * 2 + 20
    height = len(logo_lines) * lineHeight + paddingY * 2

    svg_lines = []
    for i in range(len(logo_lines)):
        y = paddingY + (i + 1) * lineHeight - 5
        logo = html.escape(logo_lines[i])
        title, val, is_header = info_rows[i]
        escaped_title = html.escape(title)
        escaped_val = html.escape(val)

        if is_header:
            line_html = f'<tspan class="logo">{logo}</tspan><tspan class="header">{escaped_val}</tspan>'
        else:
            line_html = f'<tspan class="logo">{logo}</tspan><tspan class="title">{escaped_title}</tspan><tspan class="val">{escaped_val}</tspan>'

        svg_lines.append(f'    <text x="{paddingX}" y="{y}" xml:space="preserve">{line_html}</text>')

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <style>
    text {{
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
      font-size: {fontSize}px;
    }}
    .logo {{ fill: #1793d1; font-weight: bold; }}
    .header {{ fill: #58a6ff; font-weight: bold; }}
    .title {{ fill: #58a6ff; font-weight: 600; }}
    .val {{ fill: #c9d1d9; }}
    @media (prefers-color-scheme: light) {{
      .logo {{ fill: #0078b4; }}
      .header {{ fill: #0969da; }}
      .title {{ fill: #0969da; }}
      .val {{ fill: #24292f; }}
    }}
  </style>
""" + "\n".join(svg_lines) + "\n</svg>\n"
    return svg_content

def update_readme():
    stats = load_stats()
    
    elapsed = max(int(time.time() - START_TIME), 15)
    stats["total_seconds"] = stats.get("total_seconds", 0) + elapsed
    stats["runs_count"] = stats.get("runs_count", 0) + 1
    stats["last_run"] = datetime.now(timezone.utc).isoformat()
    
    save_stats(stats)
    
    user = get_user_at_host()
    os_name = get_os_name()
    host_name = "ASUS TUF Gaming F15 FX506LH_FX506LH 1.0"
    kernel_name = get_kernel()
    uptime_str = format_uptime(stats["total_seconds"], stats["runs_count"])
    pkgs_count = get_packages()
    memory_str = get_memory()

    # Generate neofetch.svg
    svg_content = generate_neofetch_svg(user, os_name, host_name, kernel_name, uptime_str, pkgs_count, memory_str)
    with open(SVG_FILE, "w") as f:
        f.write(svg_content)

    # Generate README.md embedding neofetch.svg directly
    readme_content = f"""<p align="left">
  <img src="neofetch.svg" alt="{user}" />
</p>
"""
    with open(README_FILE, "w") as f:
        f.write(readme_content)

    print("neofetch.svg and README.md updated successfully:")
    print(svg_content)

if __name__ == "__main__":
    update_readme()
