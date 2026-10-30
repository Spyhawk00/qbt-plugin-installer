# VERSION: 1.0
# AUTHORS: qBittorrent Search Plugin Installer contributors
# RSS search works where the HTML search is challenged. A new module name
# avoids the incompatible retired tokyotoshokan plugin. One request, 200 rows.

import re
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import unquote, urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from novaprinter import prettyPrinter


class tokyotosho:
    url = 'https://www.tokyotosho.info'
    name = 'Tokyo Toshokan'
    supported_categories = {'all': '', 'anime': '1'}
    _TIMEOUT = 10

    def search(self, what, cat='all'):
        query = unquote(what).strip()
        if not query or cat not in self.supported_categories:
            return
        params = {'terms': query}
        if self.supported_categories[cat]:
            params['filter'] = self.supported_categories[cat]
        request = Request(self.url + '/rss.php?' + urlencode(params),
                          headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=self._TIMEOUT) as response:
            body = response.read()
        # The site sends only these closing tags for a zero-result search.
        if body.strip() == b'</channel>\n</rss>':
            return
        root = ElementTree.fromstring(body)
        if root.tag != 'rss' or root.find('channel') is None:
            raise ValueError('Expected a Tokyo Toshokan RSS feed')
        seen = set()
        for item in root.findall('./channel/item')[:200]:
            if item.findtext('category') == 'Non-English':
                continue
            title = item.findtext('title') or ''
            description = item.findtext('description') or ''
            magnet = re.search(r'href=["\x27](magnet:\?[^"\x27]+)', description)
            if not title or not magnet:
                continue
            link = unescape(magnet[1])
            if not re.search(r'[?&]xt=urn:btih:(?:[a-fA-F0-9]{40}|[A-Z2-7]{32})(?:&|$)', link):
                continue
            if link in seen:
                continue
            seen.add(link)
            size = re.search(r'Size:\s*([^<]+)', description)
            try:
                stamp = int(parsedate_to_datetime(item.findtext('pubDate')).timestamp())
            except (ValueError, TypeError, AttributeError):
                stamp = -1
            prettyPrinter({
                'name': title, 'link': link, 'size': size[1].strip() if size else '-1',
                'seeds': -1, 'leech': -1, 'engine_url': self.url,
                'desc_link': (item.findtext('guid') or self.url).strip(),
                'pub_date': stamp,
            })
