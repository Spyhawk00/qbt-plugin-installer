# VERSION: 2.0
# AUTHORS: tolotp (original); patched for this installer
#
# nekoBT, an anime tracker, through its JSON API (/api/v1/torrents/search).
# Results carry magnet links, seeds, leechers and size.
#
# Patched from tolotp's v1.0: it printed a Spanish "no results" sentence into
# the output on an empty search (qBittorrent shows stray text as a broken
# row), had no timeout, and went around helpers.py's proxy settings. Now it
# prints nothing when there is nothing, and uses retrieve_url().
#
# Verified working: October 2026 ("naruto": 24 results in ~3 s).

import json
import urllib.parse

try:
    from novaprinter import prettyPrinter
    from helpers import retrieve_url
except ImportError:
    pass


def _size(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return '-1'
    for unit in ('B', 'KiB', 'MiB', 'GiB', 'TiB'):
        if value < 1024:
            return '%.2f %s' % (value, unit)
        value /= 1024
    return '%.2f PiB' % value


class nekobt:
    url = 'https://nekobt.to/'
    name = 'nekoBT'
    supported_categories = {
        'all': '',
        'anime': '',
    }

    def search(self, what, cat='all'):
        query = urllib.parse.quote_plus(urllib.parse.unquote_plus(what))
        try:
            data = json.loads(retrieve_url('%sapi/v1/torrents/search?query=%s' % (self.url, query)))
        except Exception:
            return

        torrents = data
        if isinstance(data, dict):
            torrents = data.get('data', [])
            if isinstance(torrents, dict):
                torrents = torrents.get('results', torrents.get('torrents', []))
        if not isinstance(torrents, list):
            return

        for item in torrents:
            name = item.get('title') or item.get('auto_title')
            if not name:
                continue
            link = item.get('magnet')
            if not link and item.get('infohash'):
                link = 'magnet:?xt=urn:btih:%s&dn=%s' % (item['infohash'], urllib.parse.quote(name))
            if not link:
                continue
            try:
                # uploaded_at is milliseconds since the epoch, as a string
                pub_date = int(float(item.get('uploaded_at') or item.get('created_at')) / 1000)
            except (TypeError, ValueError):
                pub_date = -1
            prettyPrinter({
                'engine_url': self.url,
                'link': link,
                'name': name,
                'size': _size(item.get('filesize')),
                'seeds': item.get('seeders', -1),
                'leech': item.get('leechers', -1),
                'desc_link': '%storrents/%s' % (self.url, item.get('id')),
                'pub_date': pub_date,
            })
