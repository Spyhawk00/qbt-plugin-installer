# VERSION: 2.0
# AUTHORS: BurningMop (burning.mop@yandex.com)
#
# PATCHED for this installer (v2.0), rewritten from upstream v1.3:
#   * The site changed its results-page <title> from "Search for ..." to
#     "<query> torrents | The RarBg". Upstream only parsed a page whose title
#     matched the old text, so every search returned nothing at all.
#     Rows are now recognised by <tr class="list-entry"> instead.
#   * Upstream spawned a new thread every 0.5 s until some page reported no
#     "next" link, and every thread fetched one detail page per result row,
#     serially. A popular query fanned out into hundreds of requests. Pages
#     are now capped at _MAX_PAGES and fetched in parallel, one request each.
#   * The magnet lives only on the detail page, so `link` is the detail page
#     and download_torrent() resolves the magnet when the user picks a result
#     (the same approach the TorrentGalaxy plugin uses).

import re
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from urllib.parse import unquote

from helpers import retrieve_url
from novaprinter import prettyPrinter


class therarbg:
    url = 'https://therarbg.com'
    name = 'The RarBg'
    supported_categories = {
        'all': 'All',
        'movies': 'Movies',
        'tv': 'TV',
        'music': 'Music',
        'games': 'Games',
        'anime': 'Anime',
        'software': 'Apps',
    }

    _MAX_PAGES = 3

    _ROW_RE = re.compile(r'<tr class="list-entry">(.*?)</tr>', re.S)
    _CELL_RE = re.compile(r'<td\b[^>]*>(.*?)</td>', re.S)
    _NAME_RE = re.compile(r'<a\s+href="(/post-detail/[^"]+)"[^>]*>(.*?)</a>', re.S)
    _DATE_RE = re.compile(r'data-order="(\d+)"')
    # The size cell carries the exact byte count; its text uses &nbsp;.
    _SIZE_RE = re.compile(r'class="sizeCell" data-order="(\d+)"')
    _TAG_RE = re.compile(r'<[^>]+>')
    _MAGNET_RE = re.compile(r'href="(magnet:\?[^"]+)"')

    def _text(self, fragment):
        return unescape(self._TAG_RE.sub('', fragment)).strip()

    def _page_url(self, what, cat, page):
        if cat == 'All':
            return f'{self.url}/get-posts/order:-se:keywords:{what}/?page={page}'
        return f'{self.url}/get-posts/order:-se:category:{cat}:keywords:{what}/?page={page}'

    def _fetch(self, url):
        try:
            return retrieve_url(url)
        except Exception:  # pylint: disable=broad-exception-caught
            return ''

    def _parse(self, html):
        rows = []
        for row in self._ROW_RE.findall(html):
            try:
                cells = self._CELL_RE.findall(row)
                name = self._NAME_RE.search(row)
                if len(cells) < 8 or not name:
                    continue
                date = self._DATE_RE.search(row)
                size = self._SIZE_RE.search(row)
                desc_link = self.url + name.group(1)
                category = self._text(cells[2])
                title = self._text(name.group(2))
                rows.append({
                    'engine_url': self.url,
                    'name': f'{title} ({category})' if category else title,
                    'desc_link': desc_link,
                    'link': desc_link,
                    'size': size.group(1) if size else
                            self._text(cells[5]).replace(',', '.').replace('\xa0', ' '),
                    'seeds': self._text(cells[6]) or -1,
                    'leech': self._text(cells[7]) or -1,
                    'pub_date': int(date.group(1)) if date else -1,
                })
            except Exception:  # pylint: disable=broad-exception-caught
                continue
        return rows

    def search(self, what, cat='all'):
        category = self.supported_categories.get(cat, 'All')
        what = unquote(what).strip().replace(' ', '+')
        urls = [self._page_url(what, category, p) for p in range(1, self._MAX_PAGES + 1)]

        with ThreadPoolExecutor(len(urls)) as pool:
            pages = list(pool.map(self._fetch, urls))

        seen = set()
        for html in pages:
            rows = self._parse(html)
            for row in rows:
                if row['desc_link'] not in seen:
                    seen.add(row['desc_link'])
                    prettyPrinter(row)
            # A short page is the last one; later pages repeat or are empty.
            if len(rows) < 50:
                break

    def download_torrent(self, info):
        match = self._MAGNET_RE.search(retrieve_url(info))
        if not match:
            raise ValueError('No magnet link found on: ' + info)
        print(match.group(1) + ' ' + info)
