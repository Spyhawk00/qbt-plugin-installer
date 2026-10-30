# VERSION: 1.0
# AUTHORS: qBittorrent Search Plugin Installer contributors
# Search the published torrent catalogue, not just recent announcements.
# A second feed supplies project pages/categories. No per-result requests.

import re
from email.utils import parsedate_to_datetime
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from novaprinter import prettyPrinter


class fosstorrents:
    url = 'https://fosstorrents.com'
    name = 'FOSS Torrents'
    supported_categories = {'all': '', 'software': 'software', 'games': 'games'}
    _TIMEOUT = 8
    _MAX_RESULTS = 100

    def _feed(self, path):
        request = Request(self.url + path, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=self._TIMEOUT) as response:
            body = response.read(2 * 1024 * 1024 + 1)
        if len(body) > 2 * 1024 * 1024:
            raise ValueError('FOSS Torrents feed exceeds size limit')
        root = ElementTree.fromstring(body)
        if root.tag != 'rss' or root.find('channel') is None:
            raise ValueError('Expected a FOSS Torrents RSS catalogue')
        return root.findall('./channel/item')

    def search(self, what, cat='all'):
        query = unquote(what).strip()
        terms = re.findall(r'\w+', query.casefold())
        if not terms or cat not in self.supported_categories:
            return
        items = self._feed('/feed/torrents.xml')
        matches = []
        for item in items:
            title = item.findtext('title') or ''
            link = item.findtext('link') or ''
            words = set(re.findall(r'\w+', (title + ' ' + unquote(link.rsplit('/', 1)[-1])).casefold()))
            if not all(t in words for t in terms):
                continue
            # The catalogue publishes direct metainfo URLs, never payload URLs.
            if not re.fullmatch(r'https://fosstorrents\.com/direct-files/[^\s|?#]+\.torrent', link):
                continue
            matches.append((item, title, link))
        if not matches:
            return
        projects = {}
        for item in self._feed('/feed/rss.xml'):
            link = item.findtext('link') or ''
            match = re.fullmatch(r'https://fosstorrents\.com/(distributions|softwares|games)/([\w-]+)/?(?:\?[^\s|]*)?', link)
            if match:
                projects[match[2]] = (match[1], self.url + '/' + match[1] + '/' + match[2] + '/')
        seen = set()
        for item, title, link in matches:
            slug = re.search(r'^Torrent for ([\w-]+) - ', item.findtext('description') or '')
            project = projects.get(slug[1]) if slug else None
            if cat == 'games' and (project is None or project[0] != 'games'):
                continue
            if cat == 'software' and (project is None or project[0] not in ('softwares', 'distributions')):
                continue
            if link in seen:
                continue
            seen.add(link)
            try:
                stamp = int(parsedate_to_datetime(item.findtext('pubDate')).timestamp())
            except (ValueError, TypeError, AttributeError):
                stamp = -1
            prettyPrinter({
                'name': title, 'link': link, 'size': '-1', 'seeds': -1, 'leech': -1,
                'engine_url': self.url, 'pub_date': stamp,
                'desc_link': project[1] if project else self.url + '/search/?query=' + quote(query, safe=''),
            })
            if len(seen) >= self._MAX_RESULTS:
                break
