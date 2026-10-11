# VERSION: 1.0
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
#  * Its link is not a magnet, so a double-click runs nova2dl.py, which calls
#    download_torrent() below: that opens the release page in the browser and
#    prints nothing, and qBittorrent then quietly adds no torrent.
#
# GitHub is asked at most once a day (releases.atom, not the rate-limited
# API); the answer is kept in installer_updates.json next to this file. The
# installed version comes from qbt-plugin-installer.json, which the installer
# writes. Notify only: this never downloads or changes anything itself.

import json
import os
import re
import time
import webbrowser
from urllib.parse import unquote
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = 'https://github.com/Spyhawk00/qbt-plugin-installer'


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
                     f'Double-click here to download it.  (search: {words})'),
            'link': self._PAGE,
            'desc_link': self._PAGE,
            'size': -1,
            'seeds': -1,
            'leech': -1,
            'pub_date': -1,
        })

    def download_torrent(self, info):
        # Prints nothing on purpose: qBittorrent then adds no torrent.
        if info.startswith(_REPO + '/'):
            webbrowser.open(info)
