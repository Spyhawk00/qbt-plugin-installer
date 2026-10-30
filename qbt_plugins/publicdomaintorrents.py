# VERSION: 1.0
# AUTHORS: qBittorrent Search Plugin Installer contributors
# Search the small public catalogue locally in one request. Fetch a movie's
# download page only when selected; prefer its full-size DivX/AVI torrent.

import re
from html import unescape
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

from helpers import download_file
from novaprinter import prettyPrinter


class publicdomaintorrents:
    url = 'https://www.publicdomaintorrents.info'
    name = 'Public Domain Torrents'
    supported_categories = {'all': '', 'movies': ''}
    _API_HOSTS = ['www.publicdomaintorrents.com']
    _TIMEOUT = 10

    def _get(self, url):
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=self._TIMEOUT) as response:
            return response.read().decode('utf-8', 'replace')

    def search(self, what, cat='all'):
        terms = re.findall(r'\w+', unquote(what).casefold())
        if not terms or cat not in self.supported_categories:
            return
        html = self._get(self.url + '/nshowcat.html?category=ALL')
        pattern = r'<a\s+href=["\x27]?(nshowmovie\.html\?movieid=\d+)["\x27]?>(.*?)</a>'
        seen = set()
        for path, title in re.findall(pattern, html, re.I | re.S):
            title = unescape(re.sub(r'<[^>]+>', '', title)).strip()
            if path in seen or not all(t in title.casefold() for t in terms):
                continue
            seen.add(path)
            detail = urljoin(self.url + '/', path)
            prettyPrinter({
                'name': title, 'link': detail, 'desc_link': detail,
                'size': '-1', 'seeds': -1, 'leech': -1, 'engine_url': self.url,
            })
            if len(seen) >= 100:
                break

    def download_torrent(self, info):
        parsed = urlsplit(info)
        if parsed.netloc != 'www.publicdomaintorrents.info' or parsed.path != '/nshowmovie.html':
            raise ValueError('Unexpected movie detail URL')
        html = self._get(info)
        links = re.findall(r'href\s*=\s*["\x27]?([^\s>"\x27]+)', html, re.I)
        for link in links:
            link = unescape(link)
            parsed = urlsplit(link)
            if (parsed.netloc == 'www.publicdomaintorrents.com'
                    and parsed.path == '/bt/btdownload.php'
                    and 'type=torrent&file=' in parsed.query
                    and parsed.query.lower().endswith('.avi.torrent')):
                print(download_file('https://' + parsed.netloc + parsed.path + '?' + parsed.query))
                return
        raise ValueError('Full-size movie torrent not found')
