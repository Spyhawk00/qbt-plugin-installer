"""Offline tests for tools/health_check.py: the report, the "failing since"
dates carried in the issue body, and when the issue is opened, commented
on and closed. `gh` is replaced with a recorder; nothing reaches GitHub."""

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import health_check as hc  # noqa: E402


def result(engine, status="OK", rows=10):
    return dict(engine=engine, query="ubuntu", status=status, rows=rows, seconds=1.0, detail="")


@pytest.fixture
def gh_calls(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(hc, "gh", lambda *args, check=True: calls.append(args) or "")
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    return calls


def test_report_carries_failing_since():
    body = hc.report([result("a"), result("b", "EMPTY", 0)], [], {"b": "2026-10-05"}, "2026-10-12")
    assert "| b | ⚠️ EMPTY | 0 |" in body and "2026-10-05" in body
    state = json.loads(hc.STATE.search(body).group(1))
    assert state == {"b": "2026-10-05"}


def test_new_problem_opens_issue(gh_calls):
    hc.update_issue(None, "body", ["b empty"])
    assert any(c[:2] == ("issue", "create") for c in gh_calls)


def test_closed_issue_reopened_with_comment(gh_calls):
    hc.update_issue({"number": 7, "state": "CLOSED", "body": ""}, "body", ["b empty"])
    verbs = [c[:2] for c in gh_calls]
    assert ("issue", "edit") in verbs and ("issue", "reopen") in verbs
    comment = next(c for c in gh_calls if c[:2] == ("issue", "comment"))
    assert "b empty" in comment[-1]  # the comment is what notifies


def test_all_ok_closes_open_issue(gh_calls):
    hc.update_issue({"number": 7, "state": "OPEN", "body": ""}, "body", [])
    assert [c[:2] for c in gh_calls] == [("issue", "edit"), ("issue", "close")]


def test_all_ok_and_no_issue_does_nothing(gh_calls):
    hc.update_issue(None, "body", [])
    hc.update_issue({"number": 7, "state": "CLOSED", "body": ""}, "body", [])
    assert gh_calls == []


def test_engines_follow_install_record(tmp_path):
    engines = tmp_path / "engines"
    engines.mkdir()
    for name in ("piratebay.py", "yts.py", "installer_updates.py"):
        (engines / name).write_text("x")
    (engines / "qbt-plugin-installer.json").write_text(
        json.dumps({"version": "1.3.0", "plugins": ["piratebay.py", "yts.py", "gone.py"]}))
    assert hc.engines_in(tmp_path) == ["piratebay", "yts"]
