#!/usr/bin/env python3
"""Search with every installed engine and report which still work.

Runs each engine through nova2.py exactly as qBittorrent does, one at a
time (snowfl rate-limits parallel searches and returns zero, which looks
like a dead engine), with a query that suits its site: "ubuntu" correctly
finds nothing on an anime or movie site. An engine that fails is retried
once after a pause before it counts, since sites have bad minutes.

    python tools/health_check.py                 # your qBittorrent's engines
    python tools/health_check.py --nova3 DIR     # another nova3 folder
    python tools/health_check.py --no-pins       # skip the upstream pin check

Also lists pinned plugins with newer upstream versions (tools/refresh_pins.py).
Exit code 1 when something needs attention.

The weekly workflow (.github/workflows/health.yml) runs it with --issue:
results go to one GitHub issue labelled "engine-health", which is opened or
reopened when something fails and closed when everything passes again. The
issue body carries each engine's "failing since" date from week to week.
Developer tool: not part of the .exe.
"""

import argparse
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import install_qbt_plugins as core  # noqa: E402

# A query each site has plenty of results for. Anything not listed uses
# DEFAULT_QUERY. Plain words: nova2.py URL-encodes them itself.
QUERIES = {
    "leetx": "batman",  # Knaben's safety-filtered 1337x subset has no Ubuntu hits
    "nyaasi": "naruto",
    "subsplease": "naruto",
    "animetosho": "naruto",
    "nekobt": "naruto",
    "eztv_api": "batman",
    "sukebei": "test",
    "yts": "batman",
    "fitgirl_repacks": "cyberpunk",
    "academictorrents": "imagenet",
    "audiobookbay": "dune",
    "internetarchive": "ubuntu",
    "linuxtracker": "ubuntu",
    "tokyotosho": "naruto",
    "publicdomaintorrents": "night of the living dead",
    "fosstorrents": "blender",
    "tsukihime": "naruto",
}
DEFAULT_QUERY = "ubuntu"
TIMEOUT = 60      # seconds before a search counts as hung
SLOW = 30         # seconds; slower engines were retired for holding the Search tab
LABEL = "engine-health"
TITLE = "Engine health"
STATE = re.compile(r"<!-- health-state: (\{.*?\}) -->")
ICONS = {"OK": "✅", "EMPTY": "⚠️", "ERROR": "❌", "SLOW": "🐢", "TIMEOUT": "⏱️"}


def search(nova3: Path, engine: str) -> dict:
    """One search, as qBittorrent runs it."""
    query = QUERIES.get(engine, DEFAULT_QUERY)
    start = time.monotonic()
    try:
        r = subprocess.run([sys.executable, str(nova3 / "nova2.py"), engine, "all", *query.split()],
                           cwd=nova3, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return dict(engine=engine, query=query, status="TIMEOUT", rows=0,
                    seconds=TIMEOUT, detail=f"no answer in {TIMEOUT} s")
    seconds = time.monotonic() - start
    # One result per line: link|name|size|seeds|leech|engine_url|desc_link|pub_date
    rows = sum(1 for line in r.stdout.splitlines() if line.count("|") >= 7)
    detail = (r.stderr.strip().splitlines() or [""])[-1][:200]
    if r.returncode != 0 or "Traceback" in r.stderr:
        status = "ERROR"
    elif rows == 0:
        status = "EMPTY"
    elif seconds > SLOW:
        status = "SLOW"
    else:
        status, detail = "OK", ""
    return dict(engine=engine, query=query, status=status, rows=rows,
                seconds=round(seconds, 1), detail=detail)


def engines_in(nova3: Path) -> list:
    """The engines this installer put there: per the install record, else
    whichever of ours are present. The update notice isn't searched."""
    engines_dir = nova3 / "engines"
    record = core.read_install_record(engines_dir) or {}
    files = record.get("plugins") or [f"{name}.py" for name in core.our_engines()]
    return [Path(f).stem for f in files if (engines_dir / f).is_file()]


def check_engines(nova3: Path, retry_delay: float) -> list:
    results = []
    for engine in engines_in(nova3):
        result = search(nova3, engine)
        print(f"  {engine:<20} {result['status']:<8} {result['rows']:>5} rows  "
              f"{result['seconds']:>5} s  {result['detail']}", flush=True)
        results.append(result)
    failing = [i for i, r in enumerate(results) if r["status"] != "OK"]
    if failing:
        print(f"Retrying {len(failing)} after {retry_delay:.0f} s ...", flush=True)
        time.sleep(retry_delay)
        for i in failing:
            again = search(nova3, results[i]["engine"])
            print(f"  {again['engine']:<20} {again['status']:<8} {again['rows']:>5} rows  "
                  f"{again['seconds']:>5} s  {again['detail']}", flush=True)
            results[i] = again
    return results


def pin_drift() -> list:
    """refresh_pins.py's CHANGED lines (no diffs), or a note that it failed."""
    sys.path.insert(0, str(REPO / "tools"))
    import refresh_pins
    text = Path(core.__file__).read_text(encoding="utf-8")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            text, _ = refresh_pins.refresh_plugins(text)
            refresh_pins.refresh_framework(text)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return [f"(could not check upstream: {exc})"]
    return [line.strip() for line in buf.getvalue().splitlines() if "CHANGED" in line]


def report(results: list, drift: list, since: dict, today: str) -> str:
    lines = [f"**{TITLE} — {today}**", "",
             "| Engine | Status | Results | Time | Query | Failing since | Detail |",
             "|---|---|---|---|---|---|---|"]
    for r in results:
        detail = r["detail"].replace("|", "\\|")
        lines.append(f"| {r['engine']} | {ICONS[r['status']]} {r['status']} | {r['rows']} | "
                     f"{r['seconds']} s | {r['query']} | {since.get(r['engine'], '')} | {detail} |")
    lines += ["", "**Upstream changes since the pins:** "
              + ("none" if not drift else "")]
    lines += [f"- `{d}`" for d in drift]
    if drift:
        lines += ["", "Review with `python tools/refresh_pins.py`, then `--write` and test."]
    lines += ["", "A failure seen from GitHub's servers may not happen on a home PC (some "
              "sites treat data-centre addresses differently). Check from your own PC "
              "before retiring an engine.",
              "", f"<!-- health-state: {json.dumps(since, sort_keys=True)} -->"]
    return "\n".join(lines)


def gh(*args: str, check: bool = True) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8",
                          check=check).stdout


def find_issue():
    found = json.loads(gh("issue", "list", "--label", LABEL, "--state", "all", "--limit", "1",
                          "--json", "number,state,body"))
    return found[0] if found else None


def update_issue(issue, body: str, problems: list) -> None:
    """Open/reopen and comment when something is wrong (that's what notifies);
    otherwise close an open issue."""
    path = Path(os.environ.get("RUNNER_TEMP", ".")) / "health-body.md"
    path.write_text(body, encoding="utf-8")
    if problems:
        summary = "Needs attention: " + "; ".join(problems)
        if issue is None:
            gh("label", "create", LABEL, "--color", "D93F0B",
               "--description", "Weekly engine health check", "--force", check=False)
            gh("issue", "create", "--title", TITLE, "--label", LABEL, "--body-file", str(path))
            return
        number = str(issue["number"])
        gh("issue", "edit", number, "--body-file", str(path))
        if issue["state"] != "OPEN":
            gh("issue", "reopen", number)
        gh("issue", "comment", number, "--body", summary)
    elif issue is not None and issue["state"] == "OPEN":
        number = str(issue["number"])
        gh("issue", "edit", number, "--body-file", str(path))
        gh("issue", "close", number, "--comment", "All engines OK and every pin up to date.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--nova3", type=Path, help="nova3 folder (default: this PC's qBittorrent)")
    parser.add_argument("--retry-delay", type=float, default=60)
    parser.add_argument("--no-pins", action="store_true", help="skip the upstream pin check")
    parser.add_argument("--issue", action="store_true",
                        help="update the GitHub issue (CI; needs gh and GH_TOKEN)")
    args = parser.parse_args()

    nova3 = args.nova3
    if nova3 is None:
        location = core.locate_qbittorrent()
        if location is None:
            sys.exit("Couldn't find qBittorrent's nova3 folder; pass --nova3.")
        nova3 = location.engines_dir.parent
    print(f"Engines in {nova3}:")
    results = check_engines(nova3, args.retry_delay)
    if not results:
        sys.exit("No engines from this installer found there.")
    drift = [] if args.no_pins else pin_drift()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    issue = find_issue() if args.issue else None
    previous = STATE.search(issue["body"] or "") if issue else None
    previous = json.loads(previous.group(1)) if previous else {}
    since = {r["engine"]: previous.get(r["engine"], today)
             for r in results if r["status"] != "OK"}
    body = report(results, drift, since, today)

    problems = [f"{r['engine']} {r['status'].lower()}" for r in results if r["status"] != "OK"]
    if drift:
        problems.append(f"{len(drift)} pin(s) behind upstream")
    print()
    print(body)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(body + "\n")
    if args.issue:
        update_issue(issue, body, problems)
    elif problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
