# VERSION: 2.0
# AUTHORS: qBittorrent Search Plugin Installer contributors
# The redesigned site's public search replaces the obsolete 2017 scraper.
# Two pages maximum; no per-result HTTP requests. Magnets use the site's hash.

import re
from html import unescape
from urllib.parse import quote, unquote, urlencode
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter


class linuxtracker:
    url = 'https://linuxtracker.org'
    name = 'LinuxTracker'
    supported_categories = {'all': '', 'software': ''}
    _TIMEOUT = 10
    _MAX_PAGES = 2

    @staticmethod
    def _text(value):
        return unescape(re.sub(r'<[^>]+>', '', value)).strip()

    def search(self, what, cat='all'):
        query = unquote(what).strip()
        if not query or cat not in self.supported_categories:
            return
        seen = set()
        for page in range(1, self._MAX_PAGES + 1):
            params = urlencode({'q': query, 'page': page})
            request = Request(self.url + '/torrents/?' + params,
                              headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(request, timeout=self._TIMEOUT) as response:
                html = response.read().decode('utf-8', 'replace')
            for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', html, re.S):
                match = re.search(r'<a class="torrent-name" href="(/torrents/([a-fA-F0-9]{40})/)">(.*?)</a>', row, re.S)
                cells = re.findall(r'<td\b[^>]*>(.*?)</td>', row, re.S)
                if not match or len(cells) < 6:
                    continue
                info_hash = match[2].lower()
                if info_hash in seen:
                    continue
                seen.add(info_hash)
                title = self._text(match[3])
                # Local tracker counts only; external counts can overlap.
                counts = [re.search(r'<strong>([\d,]+)</strong>', c) for c in cells[4:6]]
                seeds, leech = [int(c[1].replace(',', '')) if c else -1 for c in counts]
                prettyPrinter({
                    'name': title, 'size': self._text(cells[3]),
                    'seeds': seeds, 'leech': leech, 'engine_url': self.url,
                    'desc_link': self.url + match[1],
                    'link': 'magnet:?xt=urn:btih:' + info_hash + '&dn=' + quote(title, safe=''),
                })
            if not re.search(r'href="\?[^"<>]*\bpage=%d(?:&|"|\b)' % (page + 1), html):
                break
