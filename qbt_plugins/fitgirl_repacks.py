# VERSION: 2.0
# AUTHORS: Custom plugin for qBittorrent
#
# Searches FitGirl Repacks (fitgirl-repacks.site) via its public WordPress
# REST API (/wp-json/wp/v2/posts). Each repack is a WordPress post whose body
# contains one or more magnet links; we return the first magnet per post.
#
# This replaces the older plugin that read https://hydralinks.cloud/sources/
# fitgirl.json, which is now behind a Cloudflare JS challenge and returns 403
# to non-browser clients (urllib can't solve it), so the old plugin crashed on
# json.loads("") and qBittorrent reported "search engine failed".
#
# Verified working: June 2026 (fitgirl-repacks.site WP REST API)

import json
import re
import html
import urllib.parse
from datetime import datetime, timezone

try:
    from novaprinter import prettyPrinter
    from helpers import retrieve_url
except ImportError:
    pass


class fitgirl_repacks:
    url = 'https://fitgirl-repacks.site/'
    name = 'FitGirl Repacks'
    supported_categories = {'all': '', 'games': ''}

    _API = 'https://fitgirl-repacks.site/wp-json/wp/v2/posts'
    _PER_PAGE = 50
    _MAX_PAGES = 2

    _MAGNET_RE = re.compile(r'magnet:\?xt=urn:btih:[^"\'<\s]+')
    _SIZE_RE = re.compile(
        r'Repack Size:?\s*(?:from\s*)?~?\s*([\d.,]+\s*(?:GB|MB|KB))', re.I)
    _TAG_RE = re.compile(r'<[^>]+>')

    def _size(self, text):
        match = self._SIZE_RE.search(text)
        return match.group(1).strip() if match else '-1'

    def _pub_date(self, post):
        stamp = post.get('date_gmt')
        if not stamp:
            return -1
        try:
            dt = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S")
            return int(dt.replace(tzinfo=timezone.utc).timestamp())
        except (ValueError, TypeError):
            return -1

    def search(self, what, cat='all'):
        query = urllib.parse.quote_plus(urllib.parse.unquote(what))

        for page in range(1, self._MAX_PAGES + 1):
            api_url = (
                f'{self._API}?search={query}'
                f'&per_page={self._PER_PAGE}&page={page}'
            )

            try:
                raw = retrieve_url(api_url)
            except Exception:
                break

            if not raw:
                break

            try:
                posts = json.loads(raw)
            except (ValueError, TypeError):
                break

            if not isinstance(posts, list) or not posts:
                break

            for post in posts:
                try:
                    content = (post.get('content') or {}).get('rendered', '')
                    magnet = self._MAGNET_RE.search(content)
                    if not magnet:
                        continue

                    title = html.unescape(
                        (post.get('title') or {}).get('rendered', 'Unknown'))
                    text = html.unescape(self._TAG_RE.sub(' ', content))

                    prettyPrinter({
                        'engine_url': self.url,
                        'name': title,
                        'desc_link': post.get('link', self.url),
                        'link': magnet.group(0),
                        'size': self._size(text),
                        'seeds': -1,
                        'leech': -1,
                        'pub_date': self._pub_date(post),
                    })
                except Exception:
                    continue

            if len(posts) < self._PER_PAGE:
                break
