# VERSION: 1.2
# AUTHORS: qbt-plugin-installer
#
# Not a torrent site. This "engine" tells the user, inside qBittorrent's
# Search tab, when a newer version of the installer that put these engines
# here has been released -- the installer itself is run once and forgotten.
#
# How it shows up (checked against qBittorrent 5.2.2's source):
#  * When a newer release exists, every search gets one extra result,
#    "Update available ...". Otherwise this engine prints nothing.
#  * qBittorrent's default "Torrent names only" filter hides any result whose
#    name lacks one of the searched words, so the user's words are appended
#    to the notice. Without them the notice would never be seen.
#  * Results keep whatever column the user last sorted by, usually Seeders
#    (descending). With no seeder count the notice sank to the bottom of
#    hundreds of rows, unseen (found testing 1.2.0 in qBittorrent 5.2.2). So
#    it claims _TOP seeders and leechers and today's date, which puts it
#    first when sorted by seeders, leechers or newest.
#  * Its link is not a magnet, so a double-click runs nova2dl.py, which calls
#    download_torrent() below. It prints nothing, so qBittorrent then quietly
#    adds no torrent.
#
# Double-click = "install it": download_torrent() fetches the newest
# release's installer .exe from this repo's GitHub release, checks it against
# the SHA-256 digest GitHub publishes for the asset, and opens it. The user
# still sees the installer's Welcome screen and clicks Install, so nothing
# changes without their say-so. Any failure (no asset yet, offline, a digest
# mismatch) falls back to opening the release page in the browser. The
# download goes to %TEMP%\qbt-plugin-installer-update and is deleted on a
# later search, once the installer has finished with it.
#
# GitHub is asked at most once a day (releases.atom, not the rate-limited
# API); the answer is kept in installer_updates.json next to this file. The
# API is called only on a double-click. The installed version comes from
# qbt-plugin-installer.json, which the installer writes. Nothing runs or is
# downloaded until the user double-clicks the notice.

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import webbrowser
from urllib.parse import unquote
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = 'https://github.com/Spyhawk00/qbt-plugin-installer'
_API = 'https://api.github.com/repos/Spyhawk00/qbt-plugin-installer/releases/latest'
_UPDATE_DIR = os.path.join(tempfile.gettempdir(), 'qbt-plugin-installer-update')


def _version(text):
    try:
        return tuple(int(part) for part in str(text).split('.'))
    except ValueError:
        return None


class installer_updates:
    url = _REPO
    name = 'Installer updates'
    # Every category, so the notice appears whichever one is searched.
    supported_categories = {cat: cat for cat in (
        'all', 'anime', 'books', 'games', 'movies', 'music', 'pictures', 'software', 'tv')}

    _FEED = _REPO + '/releases.atom'
    _PAGE = _REPO + '/releases/latest'
    _RECORD = os.path.join(_HERE, 'qbt-plugin-installer.json')
    _CACHE = os.path.join(_HERE, 'installer_updates.json')
    _EVERY = 24 * 3600
    _TIMEOUT = 5
    _UA = 'Mozilla/5.0 (compatible; qbt-plugin-installer update check)'
    _TOP = 9999999  # above any real torrent's seeder count
    _ASSET = re.compile(r'qbt-plugin-installer-\d+\.\d+\.\d+\.exe')
    _MAX_SIZE = 50 * 1024 * 1024

    @staticmethod
    def _read(path):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _latest(self):
        cache = self._read(self._CACHE)
        if time.time() - cache.get('checked', 0) < self._EVERY:
            return cache.get('latest')
        latest = cache.get('latest')
        try:
            req = Request(self._FEED, headers={'User-Agent': self._UA})
            with urlopen(req, timeout=self._TIMEOUT) as resp:
                feed = resp.read().decode('utf-8', 'replace')
            tags = re.findall(r'/releases/tag/v(\d+\.\d+\.\d+)"', feed)
            if tags:
                latest = max(tags, key=_version)
        except Exception:  # pylint: disable=broad-exception-caught
            pass  # offline or GitHub unreachable: ask again tomorrow
        try:
            with open(self._CACHE, 'w', encoding='utf-8') as f:
                json.dump({'checked': int(time.time()), 'latest': latest}, f)
        except OSError:
            pass
        return latest

    def search(self, what, cat='all'):
        # An installer downloaded by an earlier double-click: gone once it
        # has finished (a running .exe can't be deleted, so that just waits).
        if os.path.isdir(_UPDATE_DIR):
            shutil.rmtree(_UPDATE_DIR, ignore_errors=True)
        installed = _version(self._read(self._RECORD).get('version'))
        if not installed:
            return
        latest = self._latest()
        if not latest or _version(latest) <= installed:
            return
        words = unquote(what).strip()
        prettyPrinter({
            'engine_url': self.url,
            'name': (f'⬆ Update available: search engines installer v{latest}. '
                     f'Double-click here to install it.  (search: {words})'),
            'link': self._PAGE,
            'desc_link': self._PAGE,
            'size': -1,
            'seeds': self._TOP,
            'leech': self._TOP,
            'pub_date': int(time.time()),
        })

    def _fetch(self, url, timeout):
        req = Request(url, headers={'User-Agent': self._UA})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read(self._MAX_SIZE + 1)

    def _download_installer(self):
        """Path of the newest installer, downloaded and verified, else None."""
        release = json.loads(self._fetch(_API, self._TIMEOUT * 2))
        for asset in release.get('assets', []):
            name, url = asset.get('name', ''), asset.get('browser_download_url', '')
            digest = (asset.get('digest') or '').lower()
            if (self._ASSET.fullmatch(name) and digest.startswith('sha256:')
                    and url.startswith(_REPO + '/releases/download/')):
                break
        else:
            return None
        data = self._fetch(url, 120)
        if len(data) > self._MAX_SIZE or hashlib.sha256(data).hexdigest() != digest[7:]:
            return None
        os.makedirs(_UPDATE_DIR, exist_ok=True)
        path = os.path.join(_UPDATE_DIR, name)
        with open(path + '.part', 'wb') as f:
            f.write(data)
        os.replace(path + '.part', path)
        return path

    def download_torrent(self, info):
        # Prints nothing on purpose: qBittorrent then adds no torrent.
        if not info.startswith(_REPO + '/'):
            return
        try:
            path = self._download_installer() if hasattr(os, 'startfile') else None
            if path:
                os.startfile(path)  # pylint: disable=no-member  (Windows only)
                return
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        webbrowser.open(info)
