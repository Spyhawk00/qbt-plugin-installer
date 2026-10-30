# VERSION: 1.0
# AUTHORS: qBittorrent Search Plugin Installer contributors
# Searches Archive items explicitly indexed as having a BitTorrent download.
# One bounded API request; peer counts are not published by the search API.

import json
import re
from datetime import datetime
from urllib.parse import quote, unquote, urlencode
from urllib.request import Request, urlopen

from helpers import download_file
from novaprinter import prettyPrinter


class internetarchive:
    url = 'https://archive.org'
    name = 'Internet Archive'
    supported_categories = {
        'all': '', 'movies': 'movies', 'tv': 'movies', 'music': 'audio',
        'books': 'texts', 'software': 'software', 'games': 'software',
    }
    _TIMEOUT = 10

    def download_torrent(self, info):
        print(download_file(info))

    def search(self, what, cat='all'):
        if cat not in self.supported_categories:
            return
        # Quote individual terms so user input cannot alter the API's filters.
        terms = re.findall(r'\w+', unquote(what), re.UNICODE)
        if not terms:
            return
        query = 'title:(' + ' AND '.join('"%s"' % t for t in terms) + ')'
        query += ' AND format:"Archive BitTorrent"'
        query += ' AND NOT access-restricted-item:true AND NOT collection:loggedin'
        media = self.supported_categories[cat]
        if media:
            query += ' AND mediatype:' + media
        params = [('q', query), ('rows', 100), ('output', 'json'),
                  ('sort[]', 'downloads desc')]
        params += [('fl[]', field) for field in
                   ('identifier', 'title', 'item_size', 'publicdate',
                    'access-restricted-item', 'collection')]
        request = Request(self.url + '/advancedsearch.php?' + urlencode(params),
                          headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=self._TIMEOUT) as response:
            data = json.load(response)
        for doc in data.get('response', {}).get('docs', [])[:100]:
            if str(doc.get('access-restricted-item', '')).lower() == 'true':
                continue
            if 'loggedin' in (doc.get('collection') or []):
                continue
            identifier = doc.get('identifier', '')
            if not isinstance(identifier, str) or not re.fullmatch(r'[\w.-]+', identifier):
                continue
            title = doc.get('title') or identifier
            if isinstance(title, list):
                title = title[0] if title else identifier
            try:
                size = int(doc.get('item_size') or -1)
            except (ValueError, TypeError):
                size = -1
            try:
                stamp = int(datetime.fromisoformat(doc['publicdate'].replace('Z', '+00:00')).timestamp())
            except (KeyError, ValueError, TypeError, AttributeError):
                stamp = -1
            path = quote(identifier, safe='')
            prettyPrinter({
                'name': str(title), 'size': size, 'seeds': -1, 'leech': -1,
                'engine_url': self.url, 'pub_date': stamp,
                'desc_link': self.url + '/details/' + path,
                'link': self.url + '/download/' + path + '/' + path + '_archive.torrent',
            })
