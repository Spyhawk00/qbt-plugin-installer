# VERSION: 1.1
# AUTHORS: Custom plugin for qBittorrent
#
# Searches 1337x. The file and class are named "leetx" because qBittorrent
# loads an engine by its file name and a Python module cannot start with a
# digit; the Search tab shows the `name` attribute, "1337x".
#
# Every 1337x.to / 1337x.st / x1337x.* domain sits behind a Cloudflare JS
# challenge ("cf-mitigated: challenge", HTTP 403), which urllib cannot pass.
# www.1337xx.to previously served the same site without one. October 29:
# both domains now challenge requests. When direct search is unavailable,
# use Knaben API v2 restricted to 1337x, retaining its safety/adult filters.
# Fallback rows are labelled and use only validated magnets or known hashes.
# Earlier mirror verification found the same
# markup, uploads from the current week, and the info hashes on its detail
# pages match the torrents itorrents.org holds for them (names included), so
# it is a mirror of the real index rather than a clone with fake links.
# The challenged domains stay in the list after it, in case the challenge is
# ever lifted.
#
# Results link to the detail page; download_torrent() resolves the magnet
# when the user picks one, so a search costs one request per results page.

import base64
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html import unescape
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter


class leetx:
    url = 'https://www.1337xx.to'
    name = '1337x'
    _API_HOSTS = ['api.knaben.org']
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
    _TIMEOUT = 3
    _DIRECT_BUDGET = 6
    _KNABEN_TIMEOUT = 8
    _KNABEN_PAGE = 300
    _KNABEN_PAGES = 2
    _KNABEN_CATEGORIES = {
        'all': None, 'anime': '6000000', 'software': '4000000',
        'games': '4001000,7000000', 'movies': '3000000',
        'music': '1000000', 'tv': '2000000', 'books': '9000000',
    }
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

    def _get(self, url, timeout=None):
        try:
            req = Request(url, headers={'User-Agent': self._UA})
            with urlopen(req, timeout=timeout or self._TIMEOUT) as resp:
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

    @staticmethod
    def _hash(value):
        if not isinstance(value, str):
            return None
        if re.fullmatch(r'[a-fA-F0-9]{40}', value):
            return value.lower()
        if re.fullmatch(r'[A-Za-z2-7]{32}', value):
            return base64.b32decode(value.upper()).hex()
        return None

    def _magnet(self, hit):
        """Return a validated magnet and its canonical hash, never a proxy URL."""
        known = self._hash(hit.get('hash'))
        if hit.get('hash') is not None and known is None:
            return None
        supplied = hit.get('magnetUrl')
        if supplied:
            if not isinstance(supplied, str) or any(c in supplied for c in '\r\n|'):
                return None
            if not supplied.startswith('magnet:?'):
                return None
            parsed = urlsplit(supplied)
            hashes = [self._hash(xt[9:]) for xt in parse_qs(parsed.query).get('xt', [])
                      if xt.lower().startswith('urn:btih:')]
            if not hashes or any(h is None or h != hashes[0] for h in hashes):
                return None
            if known is not None and known != hashes[0]:
                return None
            return supplied, hashes[0]
        if known:
            return 'magnet:?xt=urn:btih:' + known + '&dn=' + quote(str(hit.get('title') or ''), safe=''), known
        return None

    @staticmethod
    def _number(value):
        try:
            return max(-1, int(value)) if value is not None else -1
        except (ValueError, TypeError, OverflowError):
            return -1

    def _knaben(self, what, cat):
        seen = set()
        for page in range(self._KNABEN_PAGES):
            params = {'q': what, 't': '1337x', 'o': 'liveSeeders', 'd': 'desc',
                      's': self._KNABEN_PAGE, 'f': page * self._KNABEN_PAGE, 'dead': ''}
            category = self._KNABEN_CATEGORIES[cat]
            if category:
                params['c'] = category
            request = Request('https://api.knaben.org/v2/search?' + urlencode(params),
                              headers={'User-Agent': self._UA})
            try:
                with urlopen(request, timeout=self._KNABEN_TIMEOUT) as response:
                    data = json.load(response)
                if not isinstance(data, dict) or not isinstance(data.get('hits'), list):
                    raise ValueError('Invalid Knaben search response')
            except Exception as exc:
                print('1337x via Knaben: %s' % exc, file=sys.stderr)
                return
            hits = data['hits']
            for hit in hits[:self._KNABEN_PAGE]:
                if not isinstance(hit, dict) or hit.get('trackerId') != '1337x':
                    continue
                magnet = self._magnet(hit)
                if not magnet or magnet[1] in seen or not isinstance(hit.get('title'), str):
                    continue
                seen.add(magnet[1])
                try:
                    stamp = int(datetime.fromisoformat(hit['date'].replace('Z', '+00:00')).timestamp())
                except (KeyError, TypeError, ValueError, AttributeError):
                    stamp = -1
                # Preserve live zero; only null/missing live counts fall back.
                seeds = hit.get('liveSeeders')
                peers = hit.get('livePeers')
                detail = hit.get('details') or ''
                try:
                    parsed = urlsplit(detail) if isinstance(detail, str) else None
                except ValueError:
                    parsed = None
                if (parsed is None or parsed.scheme != 'https'
                        or any(c in detail for c in '\r\n|')
                        or parsed.hostname not in {
                            '1337x.to', 'www.1337x.to', '1337x.st', 'www.1337xx.to', 'x1337x.ws'}):
                    detail = 'https://knaben.org/search/' + quote(what, safe='') + '/0/1/seeders'
                prettyPrinter({
                    'name': hit['title'] + ' [1337x via Knaben]',
                    'engine_url': self.url, 'link': magnet[0], 'desc_link': detail,
                    'size': self._number(hit.get('bytes')), 'pub_date': stamp,
                    'seeds': self._number(hit.get('seeders') if seeds is None else seeds),
                    'leech': self._number(hit.get('peers') if peers is None else peers),
                })
            if len(hits) < self._KNABEN_PAGE:
                return

    def search(self, what, cat='all'):
        query = unquote(what).strip()
        if not query or cat not in self.supported_categories:
            return
        what = quote(query, safe='')
        category = self.supported_categories.get(cat)

        # Take the first mirror that serves a real results page (a page with
        # the results table, even if empty), not a challenge or parking page.
        base = first = None
        deadline = time.monotonic() + self._DIRECT_BUDGET
        for mirror in self._MIRRORS:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            first = self._get(self._page_url(mirror, what, category, 1),
                              timeout=min(self._TIMEOUT, remaining))
            if 'coll-1 name' in first or re.search(r'<table\b[^>]*class="[^"]*table-list', first):
                base = mirror
                break
        if base is None:
            self._knaben(query, cat)
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
        if info.startswith('magnet:'):
            magnet = self._magnet({'magnetUrl': info})
            if not magnet:
                raise ValueError('Invalid magnet link')
            print(magnet[0] + ' ' + self.url)
            return
        match = self._MAGNET_RE.search(self._get(info))
        if not match:
            raise ValueError('No magnet link found on: ' + info)
        print(match.group(1) + ' ' + info)
