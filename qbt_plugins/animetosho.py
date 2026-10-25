# VERSION: 2.0
# AUTHORS: ALAA_BRAHIM, phlexis96 (original); patched for this installer
#
# Anime Tosho's JSON feed. Anime Tosho indexes Nyaa, nekoBT and others, so it
# finds releases (batches, BD rips) the single-site engines do not.
#
# Upstream (Phlexis96's v1.21) queried feed.animetosho.xyz, which now answers
# every request with a 308 redirect to feed.animetosho.net, and
# feed.animetosho.org does not answer at all. This copy goes straight to
# .net. Results carry a magnet link, seeds, leechers, size and date.
#
# Verified working: October 2026 ("naruto": 75 results in ~2 s).

import json
import urllib.parse

try:
    from novaprinter import prettyPrinter
    from helpers import retrieve_url, download_file
except ImportError:
    pass


class animetosho:
    url = 'https://animetosho.net'
    name = 'Anime Tosho'
    supported_categories = {
        'all': 'all',
        'anime': 'anime',
    }

    FEED = 'https://feed.animetosho.net/json?q='

    def download_torrent(self, info):
        print(download_file(info))

    def search(self, what, cat='all'):
        query = urllib.parse.quote_plus(urllib.parse.unquote_plus(what))
        try:
            results = json.loads(retrieve_url(self.FEED + query))
        except Exception:
            return
        if not isinstance(results, list):
            return

        for result in results:
            link = result.get('magnet_uri') or result.get('torrent_url')
            if not link:
                continue
            seeds = result.get('seeders')
            leech = result.get('leechers')
            size = result.get('total_size')
            stamp = result.get('timestamp')
            prettyPrinter({
                'engine_url': self.url,
                'link': link,
                'name': result.get('title') or result.get('torrent_name') or 'Unknown',
                'size': '%s B' % size if size is not None else '-1',
                'seeds': -1 if seeds is None else seeds,
                'leech': -1 if leech is None else leech,
                'desc_link': result.get('link', ''),
                'pub_date': int(stamp) if stamp is not None else -1,
            })
