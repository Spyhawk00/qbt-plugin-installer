# VERSION: 1.0
# AUTHORS: Custom plugin for qBittorrent
#
# Searches Torrentz2 (torrentz2.nz) — a BitTorrent meta-search engine.
# Search results are parsed from the HTML listing; magnet links are pulled
# from individual torrent detail pages on demand via download_torrent().
#
# Verified working: June 2026 (torrentz2.nz)

import re
from urllib.request import Request, urlopen
from urllib.error import URLError

try:
    from novaprinter import prettyPrinter
    from helpers import retrieve_url
except ImportError:
    pass


class torrentz2:
    url = 'https://torrentz2.nz'
    name = 'Torrentz2'
    supported_categories = {
        'all': '',
        'movies': 'movies',
        'tv': 'tv',
        'music': 'music',
        'games': 'games',
        'software': 'software',
        'anime': 'anime',
        'books': 'books',
    }

    MAX_PAGES = 5

    def _get(self, url):
        """Fetch a URL with a browser User-Agent."""
        try:
            req = Request(url, headers={
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) '
                    'Gecko/20100101 Firefox/126.0'
                )
            })
            with urlopen(req, timeout=10) as resp:
                return resp.read().decode('utf-8', errors='replace')
        except (URLError, Exception):
            return ''

    def search(self, what, cat='all'):
        for page in range(1, self.MAX_PAGES + 1):
            url = f'{self.url}/search?q={what}&sort=seeders&page={page}'
            html = self._get(url)
            if not html:
                break

            # Split HTML at each torrent entry anchor
            chunks = re.split(r'(?=href="/torrent/[a-f0-9]+")', html)
            found = 0

            for chunk in chunks[1:]:
                # Extract torrent ID and name from the anchor
                m = re.match(
                    r'href="/torrent/([a-f0-9]+)"[^>]*>([^<]+)</a>',
                    chunk
                )
                if not m:
                    continue

                torrent_id = m.group(1)
                name = m.group(2).strip()
                if not name:
                    continue

                desc_link = f'{self.url}/torrent/{torrent_id}'

                result = {
                    'engine_url': self.url,
                    'name': name,
                    'desc_link': desc_link,
                    'link': desc_link,  # download_torrent() resolves the magnet
                    'size': '-1',
                    'seeds': -1,
                    'leech': -1,
                    'pub_date': -1,
                }

                # Extract size and peer counts from text following the anchor
                remainder = chunk[m.end():][:600]

                size_m = re.search(r'(\d+(?:\.\d+)?\s*[KMGT]?B)\b', remainder)
                if size_m:
                    result['size'] = size_m.group(1)

                # Seeds and leechers appear as two consecutive integers
                nums = [int(n) for n in re.findall(r'\b(\d+)\b', remainder)
                        if 0 < int(n) < 1_000_000]
                if len(nums) >= 2:
                    result['seeds'] = nums[-2]
                    result['leech'] = nums[-1]

                prettyPrinter(result)
                found += 1

            if found == 0:
                break

            # Stop if there is no next-page link
            if 'Next' not in html:
                break

    def download_torrent(self, info):
        """
        info is the detail-page URL (https://torrentz2.nz/torrent/{id}).
        Fetch it, extract the magnet link, and print it for qBittorrent.
        """
        html = self._get(info)
        m = re.search(r'href="(magnet:[^"]+)"', html)
        if m:
            print(m.group(1) + ' ' + info)
        else:
            raise ValueError('No magnet link found on: ' + info)
