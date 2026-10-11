# VERSION: 1.2
# AUTHORS: Custom plugin for qBittorrent
#
# Uses the official YTS JSON API (/api/v2/list_movies.json) to search for movie
# torrents. YTS is a movies-only site; all categories map to the same endpoint.
#
# YTS has many interchangeable domains. The canonical yts.mx is frequently
# blocked at the DNS level by ISPs (urllib then fails with "getaddrinfo
# failed"), so we try a list of mirrors and use the first that answers. The
# JSON API is identical across them.
#
# Each movie can have multiple qualities (720p, 1080p, 2160p, etc.); each
# quality is returned as a separate result so the user can pick the one
# they want.
#
# Verified working: September 2026. The API itself now answers every request
# with "NOTICE: Base URL moving to https://movies-api.accel.li/api/v2/", so
# that host is tried first: it serves the same JSON, it is not one of the
# domains DNS filters carry, and it is where the site says the API is going.
# The yts.* mirrors stay behind it as a fallback.

import json
import urllib.parse

try:
    from novaprinter import prettyPrinter
    from helpers import retrieve_url
except ImportError:
    pass


class yts:
    url = 'https://yts.mx'
    name = 'YTS'
    supported_categories = {
        'all': '',
        'movies': '',
    }

    # Tried in order; first host that returns a valid response wins.
    # movies-api.accel.li is the endpoint the API's own status_message points
    # at and is the only one that survives a filtering resolver. yts.mx is
    # listed last because it is the most commonly DNS-blocked.
    _API_HOSTS = ['movies-api.accel.li', 'yts.gg', 'yts.rs', 'yts.am', 'yts.mx']
    _LIMIT = 50
    _MAX_PAGES = 3

    def _fetch(self, host, what, page):
        """Return parsed JSON for one page from one host, or None on failure."""
        api_url = (
            f'https://{host}/api/v2/list_movies.json?query_term={what}'
            f'&sort_by=seeds&limit={self._LIMIT}&page={page}'
        )
        try:
            raw = retrieve_url(api_url)
        except Exception:
            return None
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except (ValueError, TypeError):
            return None
        return data if data.get('status') == 'ok' else None

    # Public announce URLs to include in constructed magnet URIs
    _TRACKERS = [
        'udp://open.demonii.com:1337/announce',
        'udp://tracker.openbittorrent.com:80',
        'udp://tracker.coppersurfer.tk:6969',
        'udp://tracker.opentrackr.org:1337/announce',
        'udp://glotorrents.pw:6969/announce',
        'udp://tracker.leechers-paradise.org:6969',
        'udp://p4p.arenabg.com:1337',
    ]

    def _magnet(self, info_hash, display_name):
        dn = urllib.parse.quote(display_name)
        trackers = ''.join(f'&tr={urllib.parse.quote(t)}' for t in self._TRACKERS)
        return f'magnet:?xt=urn:btih:{info_hash}&dn={dn}{trackers}'

    def search(self, what, cat='all'):
        # Find a live mirror using the first page, then stick with it.
        host = None
        data = None
        for candidate in self._API_HOSTS:
            data = self._fetch(candidate, what, 1)
            if data is not None:
                host = candidate
                break
        if host is None:
            return

        for page in range(1, self._MAX_PAGES + 1):
            if page > 1:
                data = self._fetch(host, what, page)
            if data is None:
                break

            movies = (data.get('data') or {}).get('movies') or []
            if not movies:
                break

            for movie in movies:
                title = movie.get('title', 'Unknown')
                year = movie.get('year', '')
                desc_link = movie.get('url', self.url)
                full_title = f'{title} ({year})' if year else title

                for torrent in movie.get('torrents') or []:
                    quality = torrent.get('quality', '?')
                    t_hash = torrent.get('hash', '')
                    t_url = torrent.get('url', '')
                    seeds = torrent.get('seeds', -1)
                    peers = torrent.get('peers', -1)
                    size = torrent.get('size', '-1')
                    codec = torrent.get('video_codec', '')

                    label = f'{full_title} [{quality}]'
                    if codec:
                        label = f'{full_title} [{quality} {codec}]'

                    if t_hash:
                        link = self._magnet(t_hash, label)
                    elif t_url:
                        link = t_url
                    else:
                        continue

                    prettyPrinter({
                        'engine_url': self.url,
                        'name': label,
                        'desc_link': desc_link,
                        'link': link,
                        'size': size,
                        'seeds': seeds,
                        'leech': peers,
                        'pub_date': -1,
                    })

            # Stop if we've paged past all results
            movie_count = (data.get('data') or {}).get('movie_count', 0)
            if page * self._LIMIT >= movie_count:
                break
