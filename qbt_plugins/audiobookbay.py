# VERSION: 1.0
# AUTHORS: nKlido
#
# PATCHED for this installer (v1.0), rewritten from upstream v0.4:
#   * theaudiobookbay.se, audiobookbay.fi and audiobookbay.is no longer
#     resolve; audiobookbay.lu serves the same site. It is now tried first.
#   * Upstream used retrieve_url, which has no timeout, so a dead mirror held
#     the search for the OS connect timeout per mirror (60 s+ in testing).
#     Every request here has its own timeout.
#   * Upstream walked every results page and fetched one detail page per
#     result, serially. Pages are now capped at _MAX_PAGES and fetched in
#     parallel; size and date come from the list page, and the info hash is
#     fetched only when the user downloads a result (download_torrent).
#   * Upstream reported a fake size ("100 MB") and fake peers (1/1). The site
#     does not publish peer counts, so they are -1 (unknown).
#   * Upstream printed "No healthy url found!" to stdout, which qBittorrent
#     does not treat as a result. Nothing is printed when no mirror answers.

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html import unescape
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter


class audiobookbay:
    url = 'https://audiobookbay.lu'
    name = 'AudioBook Bay (ABB)'
    supported_categories = {'all': 'all', 'books': 'all'}

    _MIRRORS = [
        'https://audiobookbay.lu',
        'https://theaudiobookbay.se',
        'https://audiobookbay.fi',
        'https://audiobookbay.is',
    ]
    _MAX_PAGES = 3
    _TIMEOUT = 15
    _UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0'

    _POST_RE = re.compile(
        r'<div class="post"><div class="postTitle"><h2><a href="([^"]+)"[^>]*>(.*?)</a>'
        r'(.*?)(?=<div class="post">|<div class="wp-pagenavi">|$)', re.S)
    _SIZE_RE = re.compile(r"File Size: <span[^>]*>([\d.,]+)</span>\s*([KMGT]?B)", re.I)
    _DATE_RE = re.compile(r'Posted: (\d{1,2} \w{3} \d{4})')
    _LAST_PAGE_RE = re.compile(r'/page/(\d+)/[^"]*"[^>]*title="(?:&raquo;|»)(?:&raquo;|»)"')
    _HASH_RE = re.compile(r'<td>Info Hash:</td>\s*<td>([0-9a-fA-F]{40})</td>')
    _TRACKER_RE = re.compile(r'<td>((?:udp|https?)://[^<\s]+)</td>')
    _H1_RE = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)
    _TAG_RE = re.compile(r'<[^>]+>')

    _DEFAULT_TRACKERS = [
        'udp://tracker.opentrackr.org:1337/announce',
        'udp://open.stealth.si:80/announce',
        'udp://exodus.desync.com:6969/announce',
        'udp://tracker.torrent.eu.org:451/announce',
    ]

    def _get(self, url):
        try:
            req = Request(url, headers={'User-Agent': self._UA})
            with urlopen(req, timeout=self._TIMEOUT) as resp:
                return resp.read().decode('utf-8', 'replace')
        except Exception:  # pylint: disable=broad-exception-caught
            return ''

    def _page_url(self, base, what, page):
        return f'{base}/page/{page}/?s={what}&cat=all'

    def _parse(self, base, html):
        count = 0
        for href, title, body in self._POST_RE.findall(html):
            try:
                link = href if href.startswith('http') else base + href
                size = self._SIZE_RE.search(body)
                date = self._DATE_RE.search(body)
                pub_date = -1
                if date:
                    try:
                        pub_date = int(datetime.strptime(date.group(1), '%d %b %Y').timestamp())
                    except ValueError:
                        pass
                prettyPrinter({
                    'engine_url': self.url,
                    'name': unescape(self._TAG_RE.sub('', title)).strip(),
                    'desc_link': link,
                    'link': link,
                    'size': f'{size.group(1).replace(",", "")} {size.group(2)}' if size else -1,
                    'seeds': -1,
                    'leech': -1,
                    'pub_date': pub_date,
                })
                count += 1
            except Exception:  # pylint: disable=broad-exception-caught
                continue
        return count

    def search(self, what, cat='all'):
        what = quote(unquote(what).strip())

        # All mirrors have historically shared one host, so they tend to fail
        # together; still, take the first that serves a real page.
        base = first = None
        for mirror in self._MIRRORS:
            first = self._get(self._page_url(mirror, what, 1))
            if 'AudioBook Bay' in first:
                base = mirror
                break
        if base is None:
            return

        if not self._parse(base, first):
            return

        last = self._LAST_PAGE_RE.search(first)
        last_page = min(int(last.group(1)), self._MAX_PAGES) if last else 1
        urls = [self._page_url(base, what, p) for p in range(2, last_page + 1)]
        if urls:
            with ThreadPoolExecutor(len(urls)) as pool:
                for html in pool.map(self._get, urls):
                    self._parse(base, html)

    def download_torrent(self, info):
        html = self._get(info)
        match = self._HASH_RE.search(html)
        if not match:
            raise ValueError('No info hash found on: ' + info)
        heading = self._H1_RE.search(html)
        name = unescape(self._TAG_RE.sub('', heading.group(1))).strip() if heading else ''
        trackers = self._TRACKER_RE.findall(html) or self._DEFAULT_TRACKERS
        magnet = f'magnet:?xt=urn:btih:{match.group(1).lower()}'
        if name:
            magnet += '&dn=' + quote(name)
        magnet += ''.join('&tr=' + quote(t, safe='') for t in trackers)
        print(magnet + ' ' + info)
