# VERSION: 1.0
# AUTHORS: Custom plugin for qBittorrent
#
# Searches Knaben (knaben.org), an English-language index that collects
# torrents from The Pirate Bay, 1337x, Nyaa, YTS and others. It has a JSON
# API (api.knaben.org/v1, a POST with the query) that answers in about a
# second with no Cloudflare challenge, so one request returns 300 results
# sorted by seeders, magnet links included. Checked October 2026.
#
# Results from RuTracker are left out: they are Russian-language releases,
# often a third of the hits, and this installer ships English sites only.

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter


class knaben:
    url = 'https://knaben.org'
    name = 'Knaben'
    # Knaben category ids; a parent id also matches its subcategories.
    supported_categories = {
        'all': None,
        'anime': [6000000],
        'books': [9000000],
        'games': [4001000, 7000000],  # PC games, consoles
        'movies': [3000000],
        'music': [1000000],
        'software': [4000000],
        'tv': [2000000],
    }

    _API = 'https://api.knaben.org/v1'
    _PAGE = 300  # the API's largest page
    _MAX_PAGES = 2
    _TIMEOUT = 15
    _UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'
    _SKIP_TRACKERS = {'rutracker'}

    def _query(self, what, categories, start):
        body = {
            'search_type': '100%',
            'search_field': 'title',
            'query': what,
            'order_by': 'seeders',
            'order_direction': 'desc',
            'size': self._PAGE,
            'from': start,
            'hide_unsafe': True,
            'hide_xxx': True,
        }
        if categories:
            body['categories'] = categories
        try:
            req = Request(self._API, data=json.dumps(body).encode('utf-8'),
                          headers={'User-Agent': self._UA, 'Content-Type': 'application/json'})
            with urlopen(req, timeout=self._TIMEOUT) as resp:
                return json.loads(resp.read().decode('utf-8', 'replace'))
        except Exception:  # pylint: disable=broad-exception-caught
            return {}

    @staticmethod
    def _pub_date(text):
        try:
            return int(datetime.fromisoformat(text).timestamp())
        except (TypeError, ValueError):
            return -1

    def _print(self, hits, search_page, seen):
        for hit in hits:
            try:
                if hit.get('trackerId') in self._SKIP_TRACKERS:
                    continue
                link = hit.get('magnetUrl') or hit.get('link')
                key = (hit.get('hash') or link or '').lower()
                if not link or key in seen:
                    continue
                seen.add(key)
                prettyPrinter({
                    'engine_url': self.url,
                    'name': hit.get('title') or '',
                    'link': link,
                    'desc_link': hit.get('details') or search_page,
                    'size': hit.get('bytes') or -1,
                    'seeds': hit.get('seeders', -1),
                    'leech': hit.get('peers', -1),
                    'pub_date': self._pub_date(hit.get('date')),
                })
            except Exception:  # pylint: disable=broad-exception-caught
                continue

    def search(self, what, cat='all'):
        what = unquote(what).strip()
        categories = self.supported_categories.get(cat)
        search_page = f'{self.url}/search/{quote(what)}/0/1/seeders'
        seen = set()

        first = self._query(what, categories, 0)
        self._print(first.get('hits') or [], search_page, seen)
        total = (first.get('total') or {}).get('value') or 0
        starts = [self._PAGE * p for p in range(1, self._MAX_PAGES) if self._PAGE * p < total]
        if not starts:
            return
        with ThreadPoolExecutor(len(starts)) as pool:
            for page in pool.map(lambda s: self._query(what, categories, s), starts):
                self._print(page.get('hits') or [], search_page, seen)
