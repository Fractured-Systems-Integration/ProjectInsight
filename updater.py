
"""
GitHub Release Updater (no auth required).

Compares local VERSION against the latest GitHub release tag.
If a newer version exists, prompts the user with a link to the Releases page.
"""
import json
import ssl
import webbrowser
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from tkinter import messagebox

from config import VERSION, GITHUB_OWNER, GITHUB_REPO

GITHUB_API = "https://api.github.com/repos/{owner}/{repo}/releases/latest"

def _fetch_latest_tag(owner: str, repo: str):
    url = GITHUB_API.format(owner=owner, repo=repo)
    try:
        req = Request(url, headers={"User-Agent": "FSI-Insight-Updater/1.0"})
        ctx = ssl.create_default_context()
        with urlopen(req, context=ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return (data.get("tag_name") or "").lstrip("v").strip() or None
    except (URLError, HTTPError) as e:
        messagebox.showwarning("Update Check Failed", f"Could not reach GitHub: {e}")
    except Exception as e:
        messagebox.showwarning("Update Check Failed", str(e))
    return None

def _version_tuple(v: str):
    # simple semantic split: "1.4.2" -> (1,4,2)
    parts = []
    for p in v.split("."):
        num = ''.join(ch for ch in p if ch.isdigit())
        parts.append(int(num) if num else 0)
    return tuple(parts)

def run_updater():
    latest = _fetch_latest_tag(GITHUB_OWNER, GITHUB_REPO)
    if not latest:
        return
    cur = _version_tuple(VERSION)
    lat = _version_tuple(latest)

    if lat > cur:
        if messagebox.askyesno("Update Available",
                               f"A newer version is available:\n"
                               f"Current: v{VERSION}\nLatest: v{latest}\n\n"
                               f"Open releases page?"):
            webbrowser.open(f"https://github.com/Fractured-Systems-Integration/ProjectInsight.git")
    else:
        messagebox.showinfo("Up to Date", f"You are on the latest version (v{VERSION}).")
