"""Offline tests for the parts of install_qbt_plugins.py that can break
quietly. Run with:  python -m pytest

Nothing here touches the network, qBittorrent or the real plugin folder:
downloads, DNS and process lookups are replaced with fakes. The CI smoke
test covers the real install end to end.
"""

import json
import socket
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
import install_qbt_plugins as core  # noqa: E402


# ---------------------------------------------------------------------------
# enable_search_tab: line-by-line edit of qBittorrent.ini
# ---------------------------------------------------------------------------

# Qt's own escaping: backslashes in keys, @Variant/@ByteArray values. A
# configparser round trip would mangle these; the edit must not touch them.
INI = """[BitTorrent]
Session\\DefaultSavePath=C:/Users/Example/Downloads
Session\\Port=6881

[Preferences]
Downloads\\SavePath=C:/Users/Example/Downloads/
General\\Locale=en
MainWindow\\geometry=@ByteArray(\\x1\\xd9\\xd0\\xcb\\0\\x3)
Search\\SearchEnabled=false

[LegalNotice]
Accepted=true
"""


def lines_of(path):
    return path.read_text(encoding="utf-8").splitlines()


def test_search_tab_flipped_in_place(tmp_path):
    ini = tmp_path / "qBittorrent.ini"
    ini.write_text(INI, encoding="utf-8")
    assert core.enable_search_tab(ini, dry_run=False) == "OK"
    expected = INI.splitlines()
    expected[expected.index("Search\\SearchEnabled=false")] = "Search\\SearchEnabled=true"
    assert lines_of(ini) == expected


def test_search_tab_added_under_preferences(tmp_path):
    ini = tmp_path / "qBittorrent.ini"
    ini.write_text(INI.replace("Search\\SearchEnabled=false\n", ""), encoding="utf-8")
    assert core.enable_search_tab(ini, dry_run=False) == "OK"
    lines = lines_of(ini)
    assert lines[lines.index("[Preferences]") + 1] == "Search\\SearchEnabled=true"
    assert lines.count("Search\\SearchEnabled=true") == 1
    assert "MainWindow\\geometry=@ByteArray(\\x1\\xd9\\xd0\\xcb\\0\\x3)" in lines


def test_search_tab_already_on_leaves_file_alone(tmp_path):
    ini = tmp_path / "qBittorrent.ini"
    text = INI.replace("SearchEnabled=false", "SearchEnabled=true")
    ini.write_text(text, encoding="utf-8")
    before = ini.read_bytes()
    assert core.enable_search_tab(ini, dry_run=False).startswith("SKIP")
    assert ini.read_bytes() == before


def test_search_tab_key_in_other_section_is_not_ours(tmp_path):
    ini = tmp_path / "qBittorrent.ini"
    ini.write_text("[Other]\nSearch\\SearchEnabled=false\n", encoding="utf-8")
    assert core.enable_search_tab(ini, dry_run=False) == "OK"
    assert lines_of(ini) == ["[Other]", "Search\\SearchEnabled=false", "",
                             "[Preferences]", "Search\\SearchEnabled=true"]


def test_search_tab_creates_missing_file(tmp_path):
    ini = tmp_path / "config" / "qBittorrent.ini"
    assert core.enable_search_tab(ini, dry_run=False) == "OK"
    assert lines_of(ini) == ["[Preferences]", "Search\\SearchEnabled=true"]


def test_search_tab_dry_run_writes_nothing(tmp_path):
    ini = tmp_path / "qBittorrent.ini"
    ini.write_text(INI, encoding="utf-8")
    before = ini.read_bytes()
    assert core.enable_search_tab(ini, dry_run=True).startswith("DRY")
    assert ini.read_bytes() == before


# ---------------------------------------------------------------------------
# Versions and the install record
# ---------------------------------------------------------------------------

def test_parse_version():
    assert core.parse_version("1.2.0") == (1, 2, 0)
    assert core.parse_version("v1.10.0") > core.parse_version("1.9.9")
    assert core.parse_version("1.3.0-beta") is None
    assert core.parse_version(None) is None


def test_downgrade_refused_unless_forced(tmp_path, capsys):
    (tmp_path / core.INSTALL_RECORD).write_text(json.dumps({"version": "99.0.0"}))
    assert core.check_previous_install(tmp_path, force=False, dry_run=False) is False
    assert core.check_previous_install(tmp_path, force=True, dry_run=False) is True
    assert core.check_previous_install(tmp_path, force=False, dry_run=True) is True


def test_upgrade_allowed(tmp_path, capsys):
    (tmp_path / core.INSTALL_RECORD).write_text(json.dumps({"version": "1.0.0"}))
    assert core.check_previous_install(tmp_path, force=False, dry_run=False) is True
    assert "upgrading" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# download(): the pins
# ---------------------------------------------------------------------------

GOOD = b"# VERSION: 1.0\nclass x:\n    pass\n"
GOOD_HASH = core.sha256_of(GOOD)


@pytest.fixture
def fake_http(monkeypatch):
    """Replace the network: serves `fake_http.body`, records each URL."""
    class Fake:
        body = GOOD
        calls = []

        def __call__(self, url, timeout=15):
            self.calls.append(url)
            if isinstance(self.body, Exception):
                raise self.body
            return self.body
    fake = Fake()
    fake.calls = []
    monkeypatch.setattr(core, "http_get", fake)
    return fake


def test_download_installs_matching_file(tmp_path, fake_http):
    dest = tmp_path / "x.py"
    assert core.download("u", GOOD_HASH, dest, force=False, dry_run=False) == "OK"
    assert dest.read_bytes() == GOOD


def test_download_up_to_date_needs_no_network(tmp_path, fake_http):
    dest = tmp_path / "x.py"
    dest.write_bytes(GOOD)
    assert core.download("u", GOOD_HASH, dest, force=False, dry_run=False).startswith("SKIP")
    assert fake_http.calls == []


def test_download_refuses_mismatch(tmp_path, fake_http):
    fake_http.body = b"<html>captive portal</html>"
    dest = tmp_path / "x.py"
    status = core.download("u", GOOD_HASH, dest, force=False, dry_run=False)
    assert status.startswith("FAIL") and "checksum" in status
    assert not dest.exists()


def test_download_mismatch_keeps_installed_copy(tmp_path, fake_http):
    fake_http.body = b"tampered"
    dest = tmp_path / "x.py"
    dest.write_bytes(b"older version")
    status = core.download("u", GOOD_HASH, dest, force=False, dry_run=False)
    assert status.startswith("SKIP") and "checksum" in status
    assert dest.read_bytes() == b"older version"


def test_download_replaces_outdated_copy(tmp_path, fake_http):
    dest = tmp_path / "x.py"
    dest.write_bytes(b"older version")
    assert core.download("u", GOOD_HASH, dest, force=False, dry_run=False) == "OK    (updated)"
    assert dest.read_bytes() == GOOD


def test_download_offline_keeps_installed_copy(tmp_path, fake_http):
    fake_http.body = OSError("no network")
    dest = tmp_path / "x.py"
    dest.write_bytes(b"older version")
    assert core.download("u", GOOD_HASH, dest, force=False, dry_run=False).startswith("SKIP")
    assert dest.read_bytes() == b"older version"


def test_download_framework_kept_unless_forced(tmp_path, fake_http):
    dest = tmp_path / "nova2.py"
    dest.write_bytes(b"qBittorrent's own copy")
    assert core.download("u", GOOD_HASH, dest, False, False, kind="framework").startswith("SKIP")
    assert fake_http.calls == []
    assert core.download("u", GOOD_HASH, dest, True, False, kind="framework").startswith("OK")
    assert dest.read_bytes() == GOOD


def test_download_dry_run_changes_nothing(tmp_path, fake_http):
    dest = tmp_path / "x.py"
    assert core.download("u", GOOD_HASH, dest, force=False, dry_run=True).startswith("DRY")
    assert not dest.exists() and fake_http.calls == []


def test_every_pin_is_a_commit_and_a_sha256():
    pins = [(url, sha) for url, sha in core.REMOTE_PLUGINS.values()]
    pins += [(core.NOVA3_BASE + name, sha) for name, sha in core.FRAMEWORK_FILES.items()]
    for url, sha in pins:
        assert core.re.search(r"githubusercontent\.com/[^/]+/[^/]+/[0-9a-f]{40}/", url), url
        assert core.re.fullmatch(r"[0-9a-f]{64}", sha), url


# ---------------------------------------------------------------------------
# Load check
# ---------------------------------------------------------------------------

def test_capability_names():
    xml = """<capabilities>
  <piratebay>
    <name>The Pirate Bay</name>
    <url>https://thepiratebay.org</url>
    <categories>all movies tv</categories>
  </piratebay>
  <leetx>
    <name>1337x</name>
    <url>https://www.1337xx.to</url>
    <categories />
  </leetx>
</capabilities>"""
    assert core.capability_names(xml) == ["piratebay", "leetx"]
    assert core.capability_names("<capabilities />") == []
    assert core.capability_names("") == []


# ---------------------------------------------------------------------------
# Retired engines
# ---------------------------------------------------------------------------

def test_jackett_is_retired_and_cleaned_with_its_settings(tmp_path):
    assert "jackett.py" in core.RETIRED_PLUGINS
    assert "jackett" not in core.our_engines()
    for name in ("jackett.py", "jackett.ico", "jackett.json", "mine.py"):
        (tmp_path / name).write_text("x")
    assert core.remove_retired(tmp_path, dry_run=False) == ["jackett.py"]
    assert [p.name for p in tmp_path.iterdir()] == ["mine.py"]


# ---------------------------------------------------------------------------
# DNS check
# ---------------------------------------------------------------------------

def test_engine_hosts_are_url_and_api_hosts_not_mirrors():
    hosts = core.engine_hosts(REPO / "qbt_plugins" / "yts.py")
    assert hosts[0] == "yts.mx" and "movies-api.accel.li" in hosts
    # Knaben is now a working API fallback; challenged mirrors stay excluded.
    assert core.engine_hosts(REPO / "qbt_plugins" / "leetx.py") == ["www.1337xx.to", "api.knaben.org"]


@pytest.fixture
def fake_dns(monkeypatch):
    """host -> list of addresses; a missing host doesn't resolve."""
    table = {"github.com": ["140.82.112.3"]}

    def getaddrinfo(host, port, *args, **kwargs):
        if host not in table:
            raise socket.gaierror(11001, "getaddrinfo failed")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addr, port)) for addr in table[host]]
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    return table


def engine_file(engines, name, *hosts):
    api_hosts = ", ".join(f"'{h}'" for h in hosts[1:])
    (engines / f"{name}.py").write_text(
        f"class {name}:\n    url = 'https://{hosts[0]}'\n    _API_HOSTS = [{api_hosts}]\n"
        "    _MIRRORS = ['https://walled-mirror.example']\n")


def test_blocked_engines(tmp_path, fake_dns):
    engine_file(tmp_path, "fine", "fine.example")
    engine_file(tmp_path, "sunk", "sunk.example")
    engine_file(tmp_path, "gone", "gone.example")
    engine_file(tmp_path, "mirrored", "blocked.example", "mirror.example")
    fake_dns.update({"fine.example": ["93.184.216.34"], "sunk.example": ["0.0.0.0"],
                     "blocked.example": ["0.0.0.0"], "mirror.example": ["93.184.216.35"],
                     "walled-mirror.example": ["104.21.0.1"]})  # ignored: a fallback
    blocked = core.blocked_engines(tmp_path, ["fine", "sunk", "gone", "mirrored"])
    assert blocked == {"sunk": "sinkhole", "gone": "fail"}


def test_blocked_engines_offline_says_nothing(tmp_path, fake_dns):
    del fake_dns["github.com"]
    engine_file(tmp_path, "gone", "gone.example")
    assert core.blocked_engines(tmp_path, ["gone"]) is None


def test_worth_reporting():
    assert core.worth_reporting({"a": "sinkhole"})
    assert not core.worth_reporting({"a": "fail"})  # one site may just be down
    assert core.worth_reporting({"a": "fail", "b": "fail"})


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------

def test_uninstall_removes_only_ours(tmp_path, monkeypatch):
    engines = tmp_path / "nova3" / "engines"
    cache = engines / "__pycache__"
    cache.mkdir(parents=True)
    ours = ["piratebay.py", "leetx.py", core.NOTICE_PLUGIN.name]
    for name in ours + ["mine.py", "piratebay.ico",
                        "installer_updates.json", core.INSTALL_RECORD, core.INSTALL_LOG]:
        (engines / name).write_text("x")
    (cache / "leetx.cpython-313.pyc").write_text("x")
    (cache / "mine.cpython-313.pyc").write_text("x")

    monkeypatch.setattr(core, "locate_qbittorrent",
                        lambda override=None: core.QbtLocation(engines, None, None, "standard"))
    monkeypatch.setattr(core, "qbittorrent_processes", lambda: {})
    out = core.run_uninstall(core.Options(yes=True, no_restart=True), confirm=lambda s: True)

    assert out.exit_code == 0 and out.removed == 2  # the notice isn't an engine
    assert sorted(p.name for p in engines.glob("*")) == ["__pycache__", "mine.py"]
    assert [p.name for p in cache.iterdir()] == ["mine.cpython-313.pyc"]


def test_uninstall_cancelled_changes_nothing(tmp_path, monkeypatch):
    engines = tmp_path / "engines"
    engines.mkdir()
    (engines / "piratebay.py").write_text("x")
    monkeypatch.setattr(core, "locate_qbittorrent",
                        lambda override=None: core.QbtLocation(engines, None, None, "standard"))
    monkeypatch.setattr(core, "qbittorrent_processes", lambda: {})
    out = core.run_uninstall(core.Options(no_restart=True), confirm=lambda s: False)
    assert out.cancelled and (engines / "piratebay.py").exists()


# ---------------------------------------------------------------------------
# Install log
# ---------------------------------------------------------------------------

def test_tee_and_save_log(tmp_path):
    class Sink:
        text = ""

        def write(self, s):
            self.text += s
            return len(s)

        def flush(self):
            pass
    sink = Sink()
    tee = core._Tee(sink)
    tee.write("hello\n")
    assert sink.text == "hello\n"
    path = core.save_log(tmp_path, "".join(tee.parts))
    assert path.read_text(encoding="utf-8").endswith("hello\n")
    assert core._Tee(None).write("abc") == 3  # windowed .exe: no stdout at all
