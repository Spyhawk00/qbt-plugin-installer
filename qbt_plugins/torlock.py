# VERSION: 2.30
# AUTHORS: Douman (custparasite@gmx.se)
# CONTRIBUTORS: Diego de las Heras (ngosang@hotmail.es)
#
# PATCHED for this installer (v2.30):
#   * TorLock now renders the seeds cell as class="tul h2" (a second class
#     colours it by popularity). The parser matched the class attribute as a
#     whole, found no "tul", and never set "seeds" -> prettyPrinter raised
#     KeyError -> the except in search() swallowed it and the engine returned
#     nothing at all. Each class is now looked up separately, and any column
#     that still fails to parse falls back to -1 instead of losing the row.
#
# PATCHED for this installer (v2.29):
#   * handle_starttag used params["class"], which raised KeyError on result
#     rows containing a <td> with no class attribute -> the whole search
#     aborted mid-pagination and qBittorrent showed "search engine failed".
#     Now uses params.get("class").
#   * search() wraps each page fetch/parse in try/except so a single malformed
#     or failed page can never crash the search; it just stops paginating.

from datetime import datetime, timedelta
from html.parser import HTMLParser
from typing import Any, Dict, List, Tuple, Union

from helpers import download_file, retrieve_url
from novaprinter import prettyPrinter


class torlock:
    url = "https://www.torlock.com"
    name = "TorLock"
    supported_categories = {'all': 'all',
                            'anime': 'anime',
                            'software': 'software',
                            'games': 'game',
                            'movies': 'movie',
                            'music': 'music',
                            'tv': 'television',
                            'books': 'ebooks'}

    def download_torrent(self, info: str) -> None:
        print(download_file(info))

    class MyHtmlParser(HTMLParser):
        """ Sub-class for parsing results """
        def __init__(self, url: str) -> None:
            HTMLParser.__init__(self)
            self.url = url
            self.article_found = False  # true when <article> with results is found
            self.item_found = False
            self.item_bad = False  # set to True for malicious links
            self.current_item: Dict[str, Any] = {}  # dict for found item
            self.item_name: Union[str, None] = None  # key's name in current_item dict
            self.page_items = 0
            self.parser_class = {"td": "pub_date",
                                 "ts": "size",
                                 "tul": "seeds",
                                 "tdl": "leech"}

        def handle_starttag(self, tag: str, attrs: List[Tuple[str, Union[str, None]]]) -> None:
            params = dict(attrs)

            if self.item_found:
                if tag == "td":
                    param_class = params.get("class")
                    if param_class is not None:
                        # The class attribute may carry more than one class:
                        # the seeds cell is "tul h2", "tul h1", ... (the second
                        # class colours it by popularity) and some cells add
                        # "hidden-sm-down". Matching the attribute as a whole
                        # finds nothing, so look up each class separately.
                        self.item_name = None
                        for css_class in param_class.split():
                            self.item_name = self.parser_class.get(css_class)
                            if self.item_name:
                                self.current_item[self.item_name] = ""
                                break

            elif self.article_found and tag == "a":
                link = params.get("href")
                if link is not None:
                    if link.startswith("/torrent"):
                        self.current_item["desc_link"] = "".join((self.url, link))
                        self.current_item["link"] = "".join((self.url, "/tor/",
                                                             link.split('/')[2], ".torrent"))
                        self.current_item["engine_url"] = self.url
                        self.item_found = True
                        self.item_name = "name"
                        self.current_item["name"] = ""
                        self.item_bad = "rel" in params and params["rel"] == "nofollow"

            elif tag == "article":
                self.article_found = True
                self.current_item = {}

        def handle_data(self, data: str) -> None:
            if self.item_name:
                self.current_item[self.item_name] += data

        def handle_endtag(self, tag: str) -> None:
            if tag == "article":
                self.article_found = False
            elif self.item_name and (tag in ('a', 'td')):
                self.item_name = None
            elif self.item_found and tag == "tr":
                self.item_found = False
                if not self.item_bad:
                    try:
                        # Date seems like it can be Today, Yesterday, or M/D/YYYY (Timezone unknown)
                        if self.current_item["pub_date"] == "Today":
                            date = datetime.now()
                        elif self.current_item["pub_date"] == "Yesterday":
                            date = datetime.now() - timedelta(days=1)
                        else:
                            date = datetime.strptime(self.current_item["pub_date"], '%m/%d/%Y')
                        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
                        self.current_item["pub_date"] = int(date.timestamp())
                    except Exception:  # pylint: disable=broad-exception-caught
                        self.current_item["pub_date"] = -1
                    # Any column TorLock renames or drops would otherwise
                    # raise KeyError here, and search() would swallow it and
                    # return nothing at all. Report the row with the fields
                    # that did parse instead.
                    for field in ("size", "seeds", "leech"):
                        self.current_item.setdefault(field, -1)
                    prettyPrinter(self.current_item)  # type: ignore[arg-type] # refactor later
                    self.page_items += 1
                self.current_item = {}

    def search(self, query: str, cat: str = 'all') -> None:
        """ Performs search """
        query = query.replace("%20", "-")
        category = self.supported_categories[cat]

        for page in range(1, 5):
            parser = self.MyHtmlParser(self.url)
            page_url = f"{self.url}/{category}/torrents/{query}.html?sort=seeds&page={page}"
            try:
                html = retrieve_url(page_url)
                parser.feed(html)
                parser.close()
            except Exception:  # pylint: disable=broad-exception-caught
                break
            if parser.page_items < 20:
                break
