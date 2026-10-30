"""Parsing and request bounds for the engines recovered in October 2026."""

import importlib.util
import io
import json
import sys
import types
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest


@pytest.fixture
def engine(monkeypatch):
    def load(name, bodies):
        rows, requests, downloads = [], [], []
        printer = types.ModuleType('novaprinter')
        printer.prettyPrinter = rows.append
        helpers = types.ModuleType('helpers')
        helpers.download_file = lambda url: downloads.append(url) or 'downloaded.torrent ' + url
        monkeypatch.setitem(sys.modules, 'novaprinter', printer)
        monkeypatch.setitem(sys.modules, 'helpers', helpers)
        path = Path(__file__).resolve().parents[1] / 'qbt_plugins' / (name + '.py')
        spec = importlib.util.spec_from_file_location('tested_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        pending = iter(bodies)

        def get(request, timeout):
            requests.append(request.full_url)
            assert timeout == getattr(getattr(module, name), '_TIMEOUT', 10)
            return io.BytesIO(next(pending))

        monkeypatch.setattr(module, 'urlopen', get)
        return getattr(module, name)(), rows, requests, downloads
    return load


def test_archive_escapes_query_filters_and_keeps_torrent_items(engine):
    body = json.dumps({'response': {'docs': [
        {'identifier': 'sample-book', 'title': ['A book'], 'item_size': '123',
         'publicdate': '2026-10-29T00:00:00Z'},
        {'identifier': '../escape', 'title': 'bad'},
        {'identifier': 'bad-size', 'item_size': 'unknown'},
        {'identifier': 'private', 'access-restricted-item': 'true'},
        {'identifier': 'login-only', 'collection': ['loggedin']},
    ]}}).encode()
    obj, rows, requests, _ = engine('internetarchive', [body])
    obj.search('book%20OR%20mediatype%3Amovies', 'books')
    params = parse_qs(urlsplit(requests[0]).query)
    assert params['q'] == ['title:("book" AND "OR" AND "mediatype" AND "movies")'
                           ' AND format:"Archive BitTorrent"'
                           ' AND NOT access-restricted-item:true AND NOT collection:loggedin'
                           ' AND mediatype:texts']
    assert params['rows'] == ['100']
    assert len(rows) == 2
    assert rows[0]['link'].endswith('/sample-book/sample-book_archive.torrent')
    assert rows[0]['size'] == 123 and rows[0]['pub_date'] > 0
    assert rows[1]['size'] == -1


LINUX_ROW = '''<tr><td class="torrent-name-cell"><a class="torrent-name"
href="/torrents/0123456789abcdef0123456789abcdef01234567/">Ubuntu &amp; tools.iso</a></td>
<td>Ubuntu</td><td>Oct 29, 2026</td><td>2.7 GB</td>
<td><strong>12</strong><small>+2487 ext</small></td>
<td><strong>0</strong><small>+18 ext</small></td></tr>'''.replace('\n', ' ')


def test_linux_paging_deduplicates_and_uses_local_counts(engine):
    page = (LINUX_ROW + '<a href="?q=ubuntu&amp;page=2">Next</a>').encode()
    obj, rows, requests, _ = engine('linuxtracker', [page, page])
    obj.search('ubuntu')
    assert len(requests) == 2 and len(rows) == 1
    assert rows[0]['name'] == 'Ubuntu & tools.iso'
    assert rows[0]['seeds'] == 12 and rows[0]['leech'] == 0
    assert rows[0]['size'] == '2.7 GB'
    assert rows[0]['link'].endswith('&dn=Ubuntu%20%26%20tools.iso')


def test_linux_stops_when_no_next_page(engine):
    obj, rows, requests, _ = engine('linuxtracker', [LINUX_ROW.encode()])
    obj.search('ubuntu')
    assert len(rows) == len(requests) == 1


TOKYO_ITEM = '''<item><title>Naruto &amp; friends</title>
<description>&lt;a href="magnet:?xt=urn:btih:0123456789abcdef0123456789abcdef01234567&amp;dn=Naruto"&gt;Magnet&lt;/a&gt;&lt;br /&gt;Size: 2.47GB&lt;br /&gt;</description>
<guid>https://www.tokyotosho.info/details.php?id=123</guid>
<pubDate>Wed, 28 Oct 2026 22:26:08 GMT</pubDate></item>'''


def test_tokyo_preserves_xml_entities_and_uses_rss_anime_filter(engine):
    body = ('<rss><channel>' + TOKYO_ITEM * 2 + '</channel></rss>').encode()
    obj, rows, requests, _ = engine('tokyotosho', [body])
    obj.search('naruto', 'anime')
    assert parse_qs(urlsplit(requests[0]).query) == {'terms': ['naruto'], 'filter': ['1']}
    assert len(rows) == 1
    assert rows[0]['name'] == 'Naruto & friends'
    assert rows[0]['link'].endswith('&dn=Naruto')
    assert rows[0]['size'] == '2.47GB' and rows[0]['pub_date'] > 0


def test_tokyo_site_empty_search_response(engine):
    obj, rows, requests, _ = engine('tokyotosho', [b'</channel>\n</rss>'])
    obj.search('no-match')
    assert not rows and len(requests) == 1


def test_tokyo_does_not_hide_challenge_pages(engine):
    obj, _, _, _ = engine('tokyotosho', [b'<html>challenge</html>'])
    # Well-formed HTML must not be mistaken for a valid empty RSS feed.
    with pytest.raises(ValueError, match='RSS'):
        obj.search('naruto')


def test_public_catalogue_matches_all_terms_and_decodes_entities(engine):
    body = b'''<a href=nshowmovie.html?movieid=939>Night &amp; day</a>
<a href=nshowmovie.html?movieid=2>Day only</a>
<a href=nshowmovie.html?movieid=939>Night &amp; day</a>'''
    obj, rows, requests, _ = engine('publicdomaintorrents', [body])
    obj.search('night%20day')
    assert len(rows) == len(requests) == 1
    assert rows[0]['name'] == 'Night & day'
    assert rows[0]['link'].endswith('movieid=939')


def test_public_download_resolves_full_size_https_torrent(engine, capsys):
    body = b'''<a href=http://evil.test/bad.avi.torrent>ad</a>
<a href=http://www.publicdomaintorrents.com/bt/btdownload.php?type=torrent&file=Night.avi.torrent>AVI</a>'''
    obj, _, requests, downloads = engine('publicdomaintorrents', [body])
    obj.download_torrent(obj.url + '/nshowmovie.html?movieid=939')
    assert downloads == ['https://www.publicdomaintorrents.com/bt/btdownload.php?type=torrent&file=Night.avi.torrent']
    assert 'downloaded.torrent' in capsys.readouterr().out
    assert len(requests) == 1


@pytest.mark.parametrize('name', ['internetarchive', 'linuxtracker', 'tokyotosho', 'publicdomaintorrents'])
def test_empty_or_unsupported_search_makes_no_requests(engine, name):
    obj, rows, requests, _ = engine(name, [])
    obj.search('')
    obj.search('ubuntu', 'unsupported')
    assert not rows and not requests


FOSS_CATALOGUE = b'''<rss><channel>
<item><title>Blender 5.2 - Windows (x64)</title><description>Torrent for blender - Windows</description>
<link>https://fosstorrents.com/direct-files/blender-5.2-windows-x64.msi.torrent</link>
<pubDate>Wed, 28 Oct 2026 12:00:00 GMT</pubDate></item>
<item><title>0 A.D. 0.28 - Windows</title><description>Torrent for 0ad - Windows</description>
<link>https://fosstorrents.com/direct-files/0ad-0.28.exe.torrent</link></item>
<item><title>Blender unrelated payload</title><link>https://evil.test/payload.exe.torrent</link></item>
</channel></rss>'''
FOSS_PROJECTS = b'''<rss><channel>
<item><link>https://fosstorrents.com/softwares/blender/?ref=rss</link></item>
<item><link>https://fosstorrents.com/games/0ad/?ref=rss</link></item>
</channel></rss>'''


def test_foss_catalogue_matches_release_and_category_without_detail_requests(engine):
    obj, rows, requests, _ = engine('fosstorrents', [FOSS_CATALOGUE, FOSS_PROJECTS])
    obj.search('blender%20windows', 'software')
    assert len(rows) == 1 and len(requests) == 2
    assert rows[0]['desc_link'] == 'https://fosstorrents.com/softwares/blender/'
    assert rows[0]['link'].endswith('.msi.torrent')
    assert rows[0]['pub_date'] > 0 and rows[0]['seeds'] == -1


def test_foss_short_words_do_not_match_arbitrary_filename_substrings(engine):
    obj, rows, _, _ = engine('fosstorrents', [FOSS_CATALOGUE, FOSS_PROJECTS])
    obj.search('0 A.D.', 'games')
    assert [r['name'] for r in rows] == ['0 A.D. 0.28 - Windows']


def test_foss_no_match_avoids_second_request(engine):
    obj, rows, requests, _ = engine('fosstorrents', [FOSS_CATALOGUE])
    obj.search('zzqxvnonexistent')
    assert not rows and len(requests) == 1


def test_foss_deduplication_result_cap_and_unknown_category(engine):
    catalogue = FOSS_CATALOGUE.replace(b'</channel>', FOSS_CATALOGUE.split(b'<channel>')[1].split(b'</channel>')[0] + b'</channel>')
    obj, rows, _, _ = engine('fosstorrents', [catalogue, FOSS_PROJECTS])
    obj._MAX_RESULTS = 1
    obj.search('blender')
    assert len(rows) == 1


def test_foss_missing_category_mapping_is_not_misclassified(engine):
    obj, rows, _, _ = engine('fosstorrents', [FOSS_CATALOGUE, b'<rss><channel/></rss>'])
    obj.search('blender', 'games')
    assert not rows


def test_foss_challenge_page_is_not_a_valid_empty_feed(engine):
    obj, _, _, _ = engine('fosstorrents', [b'<html>challenge</html>'])
    with pytest.raises(ValueError, match='RSS'):
        obj.search('blender')


def tsuki_item(**changes):
    result = dict(id=123, name='Example Anime', btih='a' * 40, is_adult=0,
                  audiolangs=['ja'], sublangs=['en'], totalsize=1234, source_date=1793374011)
    result.update(changes)
    return result


def test_tsuki_search_needs_no_tracker_details_and_encodes_query(engine):
    body = json.dumps(dict(error=False, results=[tsuki_item()])).encode()
    obj, rows, requests, _ = engine('tsukihime', [body])
    obj.search('example%20anime', 'anime')
    assert len(requests) == 1
    assert parse_qs(urlsplit(requests[0]).query) == dict(q=['example anime'], limit=['100'], offset=['0'])
    assert rows[0]['link'].startswith('magnet:?xt=urn:btih:' + 'a' * 40)
    assert rows[0]['seeds'] == rows[0]['leech'] == -1
    assert rows[0]['size'] == 1234


def test_tsuki_filters_adult_foreign_invalid_hash_and_duplicate_rows(engine):
    items = [tsuki_item(), tsuki_item(btih='A' * 40), tsuki_item(is_adult=1),
             tsuki_item(sublangs=['fr']), tsuki_item(btih='bad'),
             tsuki_item(id='../bad'), None]
    obj, rows, _, _ = engine('tsukihime', [json.dumps(dict(results=items)).encode()])
    obj.search('example')
    assert len(rows) == 1


def test_tsuki_missing_language_metadata_cannot_claim_english(engine):
    obj, rows, _, _ = engine('tsukihime', [json.dumps(dict(results=[tsuki_item(audiolangs=None, sublangs=None)])).encode()])
    obj.search('example')
    assert not rows


@pytest.mark.parametrize('body', [dict(error=True, results=[]), dict(results=None), []])
def test_tsuki_api_errors_are_not_silent_empty_results(engine, body):
    obj, _, _, _ = engine('tsukihime', [json.dumps(body).encode()])
    with pytest.raises(ValueError, match='TsukiHime'):
        obj.search('example')


def test_tsuki_empty_results_and_minimum_query_length(engine):
    obj, rows, requests, _ = engine('tsukihime', [b'{"results":[],"error":false}'])
    obj.search('x')
    assert not requests
    obj.search('zzqxvnonexistent')
    assert not rows and len(requests) == 1
