# VERSION: 1.0
# AUTHORS: Custom plugin for qBittorrent
#
# Searches Sukebei (sukebei.nyaa.si), the adult sister site of Nyaa. Same page
# layout as nyaa.si, no Cloudflare challenge, magnet links on the results
# page. Checked October 2026. Adult content: results appear only for searches
# the user types, in the "All categories" or "Movies"/"Anime" selections.

import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter


class sukebei:
    url = 'https://sukebei.nyaa.si'
    name = 'Sukebei'
    supported_categories = {
        'all': '0_0',
        'anime': '1_0',    # Art
        'movies': '2_0',   # Real Life
    }

    _PAGES = 2  # 75 results each
    _TIMEOUT = 15
    _UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'
    _ROW = re.compile(r'<tr class="(?:default|success|danger)">(.*?)</tr>', re.S)
    _TITLE = re.compile(r'<a href="(/view/\d+)" title="([^"]*)"')
    _MAGNET = re.compile(r'href="(magnet:\?[^"]+)"')
    _CELLS = re.compile(r'<td class="text-center"[^>]*>\s*([^<\s][^<]*?)\s*</td>')
    _STAMP = re.compile(r'data-timestamp="(\d+)"')

    def _fetch(self, page_url):
        try:
            req = Request(page_url, headers={'User-Agent': self._UA})
            with urlopen(req, timeout=self._TIMEOUT) as resp:
                return resp.read().decode('utf-8', 'replace')
        except Exception:  # pylint: disable=broad-exception-caught
            return ''

    @staticmethod
    def _int(text):
        try:
            return int(text)
        except (TypeError, ValueError):
            return -1

    def _print(self, html):
        for row in self._ROW.findall(html):
            try:
                title = self._TITLE.search(row)
                magnet = self._MAGNET.search(row)
                if not title or not magnet:
                    continue
                # text-only cells in order: size, seeders, leechers, downloads
                cells = self._CELLS.findall(row)
                stamp = self._STAMP.search(row)
                prettyPrinter({
                    'engine_url': self.url,
                    'name': unescape(title.group(2)),
                    'link': unescape(magnet.group(1)),
                    'desc_link': self.url + title.group(1),
                    'size': cells[0] if cells else -1,
                    'seeds': self._int(cells[1]) if len(cells) > 1 else -1,
                    'leech': self._int(cells[2]) if len(cells) > 2 else -1,
                    'pub_date': int(stamp.group(1)) if stamp else -1,
                })
            except Exception:  # pylint: disable=broad-exception-caught
                continue

    def search(self, what, cat='all'):
        category = self.supported_categories.get(cat, '0_0')
        base = f'{self.url}/?f=0&c={category}&s=seeders&o=desc&q={what}'
        urls = [f'{base}&p={page}' for page in range(1, self._PAGES + 1)]
        with ThreadPoolExecutor(len(urls)) as pool:
            for html in pool.map(self._fetch, urls):
                self._print(html)
