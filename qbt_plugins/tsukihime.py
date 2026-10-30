# VERSION: 2.0
# AUTHORS: qBittorrent Search Plugin Installer contributors
# Custom API search: all magnet data is already present in the search response.
# Do not fetch per-release tracker details; absent tracker data is normal.

import json
import re
from urllib.parse import quote, unquote, urlencode
from urllib.request import Request, urlopen

from novaprinter import prettyPrinter


class tsukihime:
    url = 'https://tsukihime.org'
    name = 'TsukiHime'
    supported_categories = {'all': '', 'anime': ''}
    _API_HOSTS = ['api.tsukihime.org']
    _TIMEOUT = 8
    _MAX_RESULTS = 100

    @staticmethod
    def _number(value):
        try:
            return max(-1, int(value)) if value is not None else -1
        except (TypeError, ValueError, OverflowError):
            return -1

    def search(self, what, cat='all'):
        query = unquote(what).strip()
        if len(query) < 2 or cat not in self.supported_categories:
            return
        params = urlencode({'q': query, 'limit': self._MAX_RESULTS, 'offset': 0})
        request = Request('https://api.tsukihime.org/v1/search/torrents?' + params,
                          headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(request, timeout=self._TIMEOUT) as response:
            data = json.load(response)
        if not isinstance(data, dict) or data.get('error') or not isinstance(data.get('results'), list):
            raise ValueError('Invalid TsukiHime search response')
        seen = set()
        for item in data['results'][:self._MAX_RESULTS]:
            if not isinstance(item, dict) or item.get('is_adult') not in (0, False):
                continue
            languages = set()
            for field in ('audiolangs', 'sublangs'):
                values = item.get(field)
                if isinstance(values, list):
                    languages.update(v.casefold() for v in values if isinstance(v, str))
            if 'en' not in languages:
                continue
            info_hash = item.get('btih')
            title = item.get('name')
            release_id = item.get('id')
            if (not isinstance(info_hash, str) or not re.fullmatch(r'[a-fA-F0-9]{40}', info_hash)
                    or not isinstance(title, str) or not title.strip()
                    or not isinstance(release_id, int) or isinstance(release_id, bool) or release_id <= 0):
                continue
            info_hash = info_hash.lower()
            if info_hash in seen:
                continue
            seen.add(info_hash)
            prettyPrinter({
                'name': title, 'link': 'magnet:?xt=urn:btih:' + info_hash + '&dn=' + quote(title, safe=''),
                'size': self._number(item.get('totalsize')), 'seeds': -1, 'leech': -1,
                'engine_url': self.url, 'desc_link': self.url + '/view/' + str(release_id),
                'pub_date': self._number(item.get('source_date')),
            })
