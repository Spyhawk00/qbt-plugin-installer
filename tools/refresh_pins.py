#!/usr/bin/env python3
"""Move the installer's download pins forward to the latest upstream files.

Every file install_qbt_plugins.py downloads is pinned to one commit and its
SHA-256 (REMOTE_PLUGINS, NOVA3_BASE + FRAMEWORK_FILES), so users get exactly
what was tested. This finds what changed upstream since:

  * each remote plugin: the last commit on its repo's default branch that
    touched the file;
  * the nova3 framework: qBittorrent's latest release.

and prints the diff of every file that changed. Read it -- this is code
that will run on users' PCs -- then rerun with --write to update the pins,
and test the changed engines before releasing (see CLAUDE.md).

    python tools/refresh_pins.py           # report and show diffs
    python tools/refresh_pins.py --write   # also update install_qbt_plugins.py

Set GITHUB_TOKEN to avoid GitHub's limit of 60 unauthenticated API calls an
hour. Developer tool: not part of the .exe.
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "install_qbt_plugins.py"
sys.path.insert(0, str(REPO))
import install_qbt_plugins as core  # noqa: E402

RAW = re.compile(r"https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([0-9a-f]{40})/(.+)")


def get(url: str) -> bytes:
    headers = {"User-Agent": "qbt-plugin-installer refresh_pins"}
    if "api.github.com" in url:
        headers["Accept"] = "application/vnd.github+json"
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return r.read()


def show_diff(name: str, old: bytes, new: bytes) -> None:
    lines = difflib.unified_diff(old.decode("utf-8", "replace").splitlines(),
                                 new.decode("utf-8", "replace").splitlines(),
                                 f"{name} (pinned)", f"{name} (upstream)", lineterm="")
    for line in lines:
        print("    " + line)


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        sys.exit(f"error: expected exactly one {old!r} in {SCRIPT.name}")
    return text.replace(old, new)


def refresh_plugins(text: str) -> tuple:
    changed = 0
    for filename, (url, pinned_hash) in core.REMOTE_PLUGINS.items():
        owner, repo, ref, path = RAW.match(url).groups()
        commits = json.loads(get(f"https://api.github.com/repos/{owner}/{repo}"
                                 f"/commits?path={path}&per_page=1"))
        latest = commits[0]["sha"]
        if latest == ref:
            print(f"  {filename:<22} up to date ({ref[:10]})")
            continue
        new = get(f"https://raw.githubusercontent.com/{owner}/{repo}/{latest}/{path}")
        new_hash = hashlib.sha256(new).hexdigest()
        date = commits[0]["commit"]["committer"]["date"][:10]
        print(f"  {filename:<22} CHANGED {ref[:10]} -> {latest[:10]} ({date})")
        show_diff(filename, get(url), new)
        text = replace_once(text, f"/{ref}/{path}\"", f"/{latest}/{path}\"")
        text = replace_once(text, f"\"{pinned_hash}\"", f"\"{new_hash}\"")
        changed += 1
    return text, changed


def refresh_framework(text: str) -> tuple:
    release = json.loads(get("https://api.github.com/repos/qbittorrent/qBittorrent/releases/latest"))
    tag = release["tag_name"]
    latest = json.loads(get(f"https://api.github.com/repos/qbittorrent/qBittorrent/commits/{tag}"))["sha"]
    owner, repo, ref, base_path = RAW.match(core.NOVA3_BASE).groups()
    if latest == ref:
        print(f"  {'nova3 framework':<22} up to date ({tag})")
        return text, 0
    print(f"  {'nova3 framework':<22} CHANGED -> {tag} ({latest[:10]})")
    new_base = core.NOVA3_BASE.replace(ref, latest)
    for fname, pinned_hash in core.FRAMEWORK_FILES.items():
        new = get(new_base + fname)
        new_hash = hashlib.sha256(new).hexdigest()
        if new_hash == pinned_hash:
            continue
        print(f"    {fname}:")
        show_diff(fname, get(core.NOVA3_BASE + fname), new)
        text = replace_once(text, f"\"{pinned_hash}\"", f"\"{new_hash}\"")
    text = replace_once(text, f"/{ref}/", f"/{latest}/")
    version = tag.replace("release-", "")
    text = re.sub(r"\(release-[\d.]+\)", f"({tag})", text)
    text = re.sub(r"qBittorrent [\d.]+ writes itself", f"qBittorrent {version} writes itself", text)
    return text, 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--write", action="store_true",
                        help="update the pins in install_qbt_plugins.py")
    args = parser.parse_args()

    text = SCRIPT.open(encoding="utf-8", newline="").read()
    print("Remote plugins:")
    text, plugins = refresh_plugins(text)
    print("Framework:")
    text, framework = refresh_framework(text)

    if not plugins + framework:
        print("\nEverything is pinned to the latest upstream files.")
    elif args.write:
        SCRIPT.open("w", encoding="utf-8", newline="").write(text)
        print(f"\nUpdated {SCRIPT.name}. Test the changed engines, then add a CHANGELOG entry.")
    else:
        print("\nRead the diffs above, then rerun with --write to update the pins.")


if __name__ == "__main__":
    main()
