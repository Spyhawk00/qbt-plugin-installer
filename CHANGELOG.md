# Changelog

The installer uses [semantic versioning](https://semver.org): `MAJOR.MINOR.PATCH`.
The version lives in one place, `__version__` in `install_qbt_plugins.py`.

| Bump      | When                                                                 |
|-----------|----------------------------------------------------------------------|
| **MAJOR** | A change that can break an existing setup: new requirements (e.g. a newer minimum Python), a different install location, removing a command-line option. |
| **MINOR** | Engines added or removed, or a new installer feature.                |
| **PATCH** | Fixes only: a plugin repaired, a bug fixed, docs. The engine list is unchanged. |

To release: bump `__version__`, add a section below, then push a tag
`v<version>` (e.g. `v1.2.0`). The build workflow refuses a tag that does not
match `__version__`.

Versions before 1.2.0 were not numbered when they shipped; 1.0.0 and 1.1.0
are assigned after the fact so the history reads in order.

## 1.2.0 — 2026-10-10

### Added
- **A graphical installer.** The `.exe` now opens a window instead of a
  console: it shows what it found on the PC (qBittorrent, Python, the plugin
  folder, the installed version) and exactly what will happen, then a live
  progress list and a clear result.
- **Sets up everything search needs** in the user's existing qBittorrent:
  installs Python if it's missing (official python.org installer, pinned and
  checksum-verified, per-user, no admin prompt), turns on the Search tab, and
  closes and reopens qBittorrent so the engines load. The user is told about
  each of these before it happens. qBittorrent itself is never installed.
- **Finds qBittorrent's folders automatically**, including portable installs,
  registry-registered installs, Flatpak and XDG locations.
- `--yes` (don't ask) and `--no-restart` (leave qBittorrent running).
- **A smaller download:** the `.exe` is 7.8 MB instead of 11.8 MB. Downloads now
  use Windows' built-in HTTPS (which also follows the PC's proxy settings), so
  Python's OpenSSL no longer ships inside it, and unused parts of Python and
  Tcl/Tk are left out.
- **No leftover files.** Retiring an engine removes everything it left behind
  (favicon, settings/log files, Python's compiled cache), even when the
  engine's .py was removed by an earlier version. The Python setup runs from
  a private temp folder, logs included, that is deleted afterwards.
- **Version numbers.** The installer prints its version at launch, has a
  `--version` flag, and records the version it installed in
  `nova3/engines/qbt-plugin-installer.json`. Re-running says which version it
  is upgrading from, and refuses to downgrade a newer install unless
  `--force`.
- **Knaben** (`knaben.py`), an English index that searches The Pirate Bay,
  1337x, Nyaa, YTS and others at once through its API: hundreds of results
  in 2–3 seconds, in every category.
- **1337x** (`leetx.py`), through the www.1337xx.to mirror. Every 1337x.to /
  1337x.st / x1337x.* domain is behind a Cloudflare challenge.
- **Upgrading in place.** Re-running brings an older install fully up to date
  without `--force`: downloaded and bundled plugins are replaced when they
  differ, and retired engines are deleted.

### Changed
- **TheRARBG** rewritten: the site changed its results page and the plugin
  returned nothing.
- **AudioBook Bay** rewritten: its mirrors died; it now uses audiobookbay.lu,
  with timeouts and bounded paging.
- `--force` now only means "rewrite even unchanged files, including the nova3
  framework files".
- The download is named after its version, e.g.
  `qbt-plugin-installer-1.2.0.exe`.

### Removed
- **TorLock**: every domain is behind a Cloudflare challenge.
- **RuTor**: a Russian tracker with Russian-language releases. The installer
  now ships English sites only.
- **TorrentGalaxy** (~87 s per search) and **TorrentDownload** (~24 s): too slow.
- Existing copies of these, plus EZTV, Tokyo Toshokan and the engines removed
  in 1.0.0/1.1.0, are deleted when the installer is re-run.

### Fixed
- In the `.exe`, the package auto-installer would have run the installer
  itself instead of Python.
- The `.bat` launcher's Microsoft Store stub check never ran.
- The `.exe` run with arguments from a program that has no console asked
  for an Enter key to close a window that didn't exist.

## 1.1.0 — September 2026

### Added
- torrentdownload, TorrentGalaxy, TheRARBG and snowfl.

### Removed
- BitSearch, BTDig, GloTorrents and Torrentz2 (dead).

## 1.0.0 — June 2026

- First release: 17 verified engines. FitGirl Repacks rebuilt on the
  WordPress REST API, YTS mirror fallback, TorLock crash fix.
- Removed MagnetDL, DODI Repacks, 1337x, Kickass Torrents, EZTV and Zooqle
  (dead or Cloudflare-walled).
