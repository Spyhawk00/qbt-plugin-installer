# VERSION: 1.0
# AUTHORS: Custom plugin for qBittorrent
#
# Searches EZTV (eztvx.to) for TV episodes through its JSON API. EZTV's own
# search page sits behind a Cloudflare challenge, but the API does not, and
# it takes an IMDb id rather than a search word. So a search first asks IMDb's
# public suggestion endpoint which TV series match the words (at most
# _MAX_SHOWS), then lists each series' newest releases from EZTV, magnet links
# included. Words that match no series (a movie, a single episode code) give
# no results. Checked October 2026.

import json
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter


class eztv_api:
    url = 'https://eztvx.to'
    name = 'EZTV'
    supported_categories = {'all': '', 'tv': ''}

    _API = 'https://eztvx.to/api/get-torrents'
    _IMDB = 'https://v2.sg.media-imdb.com/suggestion/{}/{}.json'
    _MAX_SHOWS = 3
    _PAGE = 100
    _PAGES = 2
    _TIMEOUT = 15
    _UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'

    def _get_json(self, request_url):
        try:
            req = Request(request_url, headers={'User-Agent': self._UA})
            with urlopen(req, timeout=self._TIMEOUT) as resp:
                return json.loads(resp.read().decode('utf-8', 'replace'))
        except Exception:  # pylint: disable=broad-exception-caught
            return {}

    def _shows(self, what):
        """IMDb ids (without 'tt') of the TV series matching the words."""
        query = what.lower()
        if not query:
            return []
        data = self._get_json(self._IMDB.format(quote(query[0], safe=''), quote(query)))
        ids = []
        for item in data.get('d') or []:
            if item.get('qid') in ('tvSeries', 'tvMiniSeries') and str(item.get('id', '')).startswith('tt'):
                ids.append(item['id'][2:])
        return ids[:self._MAX_SHOWS]

    def _print(self, data):
        for torrent in data.get('torrents') or []:
            try:
                link = torrent.get('magnet_url')
                if not link:
                    continue
                prettyPrinter({
                    'engine_url': self.url,
                    'name': torrent.get('title') or torrent.get('filename') or '',
                    'link': link,
                    'desc_link': torrent.get('episode_url') or self.url,
                    'size': int(torrent.get('size_bytes') or -1),
                    'seeds': int(torrent.get('seeds') or 0),
                    'leech': int(torrent.get('peers') or 0),
                    'pub_date': int(torrent.get('date_released_unix') or -1),
                })
            except Exception:  # pylint: disable=broad-exception-caught
                continue

    def search(self, what, cat='all'):
        what = unquote(what).strip()
        urls = [f'{self._API}?limit={self._PAGE}&page={page}&imdb_id={show}'
                for show in self._shows(what)
                for page in range(1, self._PAGES + 1)]
        if not urls:
            return
        with ThreadPoolExecutor(len(urls)) as pool:
            for data in pool.map(self._get_json, urls):
                self._print(data)
