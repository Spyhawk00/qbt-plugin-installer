# VERSION: 1.0
# AUTHORS: Custom plugin for qBittorrent
#
# Searches 1337x. The file and class are named "leetx" because qBittorrent
# loads an engine by its file name and a Python module cannot start with a
# digit; the Search tab shows the `name` attribute, "1337x".
#
# Every 1337x.to / 1337x.st / x1337x.* domain sits behind a Cloudflare JS
# challenge ("cf-mitigated: challenge", HTTP 403), which urllib cannot pass.
# www.1337xx.to serves the same site without one. Checked October 2026: same
# markup, uploads from the current week, and the info hashes on its detail
# pages match the torrents itorrents.org holds for them (names included), so
# it is a mirror of the real index rather than a clone with fake links.
# The challenged domains stay in the list after it, in case the challenge is
# ever lifted.
#
# Results link to the detail page; download_torrent() resolves the magnet
# when the user picks one, so a search costs one request per results page.

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html import unescape
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter


class leetx:
    url = 'https://www.1337xx.to'
    name = '1337x'
    supported_categories = {
        'all': None,
        'anime': 'Anime',
        'software': 'Apps',
        'games': 'Games',
        'movies': 'Movies',
        'music': 'Music',
        'tv': 'TV',
        'books': 'Other',
    }

    _MIRRORS = [
        'https://www.1337xx.to',
        'https://1337x.to',
        'https://1337x.st',
        'https://x1337x.ws',
    ]
    _MAX_PAGES = 5  # 20 results per page
    _TIMEOUT = 15
    _UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'

    _ROW_RE = re.compile(r'<tr>\s*<td class="coll-1 name">(.*?)</tr>', re.S)
    _NAME_RE = re.compile(r'<a href="(/torrent/\d+/[^"]*)">(.*?)</a>', re.S)
    _SEEDS_RE = re.compile(r'<td class="coll-2 seeds">(\d+)')
    _LEECH_RE = re.compile(r'<td class="coll-3 leeches">(\d+)')
    _DATE_RE = re.compile(r'<td class="coll-date">([^<]*)')
    # The size cell is "1.1 GB" on the mirror and "1.1 GB<span ...>" on 1337x.
    _SIZE_RE = re.compile(r'<td class="coll-4 size[^"]*">([^<]*)')
    _MAGNET_RE = re.compile(r'href="(magnet:\?xt=urn:btih:[^"]+)"')
    _TAG_RE = re.compile(r'<[^>]+>')
    # "Jun. 20th  '17"; uploads from today show a time ("8am") instead.
    _DAY_RE = re.compile(r"([A-Z][a-z]{2})\.?\s+(\d{1,2})\w*\s+'(\d{2})")

    def _get(self, url):
        try:
            req = Request(url, headers={'User-Agent': self._UA})
            with urlopen(req, timeout=self._TIMEOUT) as resp:
                return unescape(resp.read().decode('utf-8', 'replace'))
        except Exception:  # pylint: disable=broad-exception-caught
            return ''

    def _page_url(self, base, what, cat, page):
        if cat:
            return f'{base}/sort-category-search/{what}/{cat}/seeders/desc/{page}/'
        return f'{base}/sort-search/{what}/seeders/desc/{page}/'

    def _pub_date(self, text):
        match = self._DAY_RE.search(text)
        if not match:
            # A bare time of day means it was uploaded today.
            return int(datetime.now().replace(hour=0, minute=0, second=0,
                                              microsecond=0).timestamp()) if text.strip() else -1
        try:
            day = datetime.strptime(' '.join(match.groups()), '%b %d %y')
            return int(day.timestamp())
        except ValueError:
            return -1

    def _parse(self, base, html, seen):
        count = 0
        for row in self._ROW_RE.findall(html):
            try:
                name = self._NAME_RE.search(row)
                if not name:
                    continue
                count += 1
                link = base + name.group(1)
                if link in seen:
                    continue
                seen.add(link)
                seeds = self._SEEDS_RE.search(row)
                leech = self._LEECH_RE.search(row)
                size = self._SIZE_RE.search(row)
                date = self._DATE_RE.search(row)
                prettyPrinter({
                    'engine_url': self.url,
                    'name': self._TAG_RE.sub('', name.group(2)).strip(),
                    'desc_link': link,
                    'link': link,
                    'size': size.group(1).replace(',', '').strip() if size else -1,
                    'seeds': seeds.group(1) if seeds else -1,
                    'leech': leech.group(1) if leech else -1,
                    'pub_date': self._pub_date(date.group(1)) if date else -1,
                })
            except Exception:  # pylint: disable=broad-exception-caught
                continue
        return count

    def search(self, what, cat='all'):
        what = quote(unquote(what).strip())
        category = self.supported_categories.get(cat)

        # Take the first mirror that serves a real results page (a page with
        # the results table, even if empty), not a challenge or parking page.
        base = first = None
        for mirror in self._MIRRORS:
            first = self._get(self._page_url(mirror, what, category, 1))
            if 'coll-1 name' in first:
                base = mirror
                break
        if base is None:
            return

        seen = set()
        if self._parse(base, first, seen) < 20:
            return

        urls = [self._page_url(base, what, category, p) for p in range(2, self._MAX_PAGES + 1)]
        with ThreadPoolExecutor(len(urls)) as pool:
            for html in pool.map(self._get, urls):
                # A short page is the last one; later pages come back empty.
                if self._parse(base, html, seen) < 20:
                    break

    def download_torrent(self, info):
        match = self._MAGNET_RE.search(self._get(info))
        if not match:
            raise ValueError('No magnet link found on: ' + info)
        print(match.group(1) + ' ' + info)
