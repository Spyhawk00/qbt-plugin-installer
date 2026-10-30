# Changelog

The installer uses [semantic versioning](https://semver.org), and the version
is set automatically: commits follow [Conventional Commits](https://www.conventionalcommits.org),
and [release-please](https://github.com/googleapis/release-please) works out
the next number, edits `__version__` in `install_qbt_plugins.py` and writes
the entries below from the commit messages. Nothing here is edited by hand
for new versions.

| Commit            | Bump      | Use it for                                                |
|-------------------|-----------|-----------------------------------------------------------|
| `fix:`            | **PATCH** | A plugin repaired, a bug fixed. The engine list is unchanged. |
| `feat:`           | **MINOR** | Engines added or removed, or a new installer feature.     |
| `feat!:` or a `BREAKING CHANGE:` footer | **MAJOR** | Can break an existing setup: a newer minimum Python, a different install location, a removed command-line option. |
| `docs:` `test:` `chore:` `ci:` `refactor:` | none | Nothing user-facing; no release by themselves. |

To release: merge the "release PR" release-please keeps open. That tags
`v<version>` and the build attaches the `.exe` to the GitHub Release.

Versions before 1.2.0 were not numbered when they shipped; 1.0.0 and 1.1.0
are assigned after the fact so the history reads in order.

## [1.4.0](https://github.com/Spyhawk00/qbt-plugin-installer/compare/v1.3.0...v1.4.0) (2026-10-30)


### Features

* add six search engines and a Knaben fallback for 1337x ([007d417](https://github.com/Spyhawk00/qbt-plugin-installer/commit/007d41720271036715193461cf4b131d8b5dc34f))

## [1.3.0](https://github.com/Spyhawk00/qbt-plugin-installer/compare/v1.2.0...v1.3.0) (2026-10-25)


### Features

* add EZTV, Sukebei, Anime Tosho, nekoBT and Pirateiro engines ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))
* add tools/refresh_pins.py and tools/health_check.py, with offline tests ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))
* check that every engine starts after installing, and say why one doesn't ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))
* drop Jackett, which needs a separate server and otherwise only adds an ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))
* pin every download to a commit and SHA-256, and check it ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))
* remove engines from the installer's first screen, or with --uninstall ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))
* save the install log as qbt-plugin-installer.log ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))
* say which sites a DNS filter, VPN or provider is blocking ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))


### Bug Fixes

* a real install crashed on an undefined variable left over from the Jackett removal ([17c1585](https://github.com/Spyhawk00/qbt-plugin-installer/commit/17c1585933df5d8cff0ce574c8e70ccdfd7acaaa))
* remove the unused TorLock, Torrentz2 and torrentdownload copies that ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))
* write the log when the .exe runs from a command line with its output ([38ccd16](https://github.com/Spyhawk00/qbt-plugin-installer/commit/38ccd16184494b61c96ba39902e4dafdd9187220))

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
- **Update notices with one-click install.** When a newer version is
  released, searches in qBittorrent show one "⬆ Update available" result at
  the top. Double-clicking it downloads the new installer from this
  project's GitHub release, checks it against the SHA-256 checksum GitHub
  publishes, and opens it; the installer still waits for Install. If
  anything goes wrong it opens the download page instead, and the download
  is deleted afterwards. GitHub is asked at most once a day. The installer's
  own window also links to a newer version.
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
- **LimeTorrents** is the official plugin again (its old domain now
  redirects). The bundled patched copy had a version qBittorrent couldn't
  read, so it logged a warning at every start.
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
