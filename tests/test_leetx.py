"""1337x direct search and Knaben fallback, without network or qBittorrent."""

import base64
import importlib.util
import io
import json
import sys
import types
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest


HASH = '0123456789abcdef0123456789abcdef01234567'


def hit(**changes):
    value = dict(trackerId='1337x', title='Example', hash=HASH,
                 magnetUrl='magnet:?xt=urn:btih:' + HASH, bytes=123,
                 seeders=50, peers=30, liveSeeders=0, livePeers=2,
                 date='2026-10-29T12:00:00+00:00',
                 details='https://1337x.to/torrent/123/Example/')
    value.update(changes)
    return value


@pytest.fixture
def plugin(monkeypatch):
    rows = []
    printer = types.ModuleType('novaprinter')
    printer.prettyPrinter = rows.append
    monkeypatch.setitem(sys.modules, 'novaprinter', printer)
    path = Path(__file__).resolve().parents[1] / 'qbt_plugins' / 'leetx.py'
    spec = importlib.util.spec_from_file_location('tested_leetx', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    obj = module.leetx()
    requests = []

    def respond(pages):
        pending = iter(pages)

        def get(request, timeout):
            requests.append(request.full_url)
            assert timeout == 8
            body = next(pending)
            if isinstance(body, Exception):
                raise body
            return io.BytesIO(json.dumps(body).encode())
        monkeypatch.setattr(module, 'urlopen', get)
    monkeypatch.setattr(obj, '_get', lambda *args, **kwargs: '')
    return obj, rows, requests, respond, module


def test_challenge_fallback_filters_source_category_and_labels_rows(plugin):
    obj, rows, requests, respond, _ = plugin
    respond([{'hits': [hit()]}])
    obj.search('example%20title', 'movies')
    params = parse_qs(urlsplit(requests[0]).query, keep_blank_values=True)
    assert params == dict(q=['example title'], t=['1337x'], o=['liveSeeders'],
                          d=['desc'], s=['300'], f=['0'], dead=[''], c=['3000000'])
    assert rows[0]['name'] == 'Example [1337x via Knaben]'
    assert rows[0]['seeds'] == 0 and rows[0]['leech'] == 2
    assert rows[0]['link'] == 'magnet:?xt=urn:btih:' + HASH


def test_known_hash_builds_magnet_and_null_live_counts_fall_back(plugin):
    obj, rows, _, respond, _ = plugin
    respond([{'hits': [hit(magnetUrl=None, liveSeeders=None, livePeers=None)]}])
    obj.search('example')
    assert rows[0]['link'].endswith(HASH + '&dn=Example')
    assert rows[0]['seeds'] == 50 and rows[0]['leech'] == 30


def test_rejects_wrong_source_proxy_only_and_inconsistent_hashes(plugin):
    obj, rows, _, respond, _ = plugin
    respond([{'hits': [None, hit(trackerId='thepiratebay'),
                       hit(hash=None, magnetUrl=None, link='https://knaben.org/live/dl/1337x/'),
                       hit(hash='f' * 40), hit(hash='broken'),
                       hit(magnetUrl='https://evil.test/torrent'),
                       hit(magnetUrl='magnet:?xt=urn:btih:bad')]}])
    obj.search('example')
    assert not rows


def test_deduplicates_base32_and_hex_magnets(plugin):
    obj, rows, _, respond, _ = plugin
    encoded = base64.b32encode(bytes.fromhex(HASH)).decode()
    respond([{'hits': [hit(), hit(hash=None, magnetUrl='magnet:?xt=urn:btih:' + encoded)]}])
    obj.search('example')
    assert len(rows) == 1


def test_caps_pagination_and_deduplicates_between_pages(plugin):
    obj, rows, requests, respond, _ = plugin
    obj._KNABEN_PAGE = 2
    page = {'hits': [hit(), hit(hash='f' * 40, magnetUrl=None)]}
    respond([page, page])
    obj.search('example')
    assert len(requests) == 2 and len(rows) == 2
    assert parse_qs(urlsplit(requests[1]).query)['f'] == ['2']


@pytest.mark.parametrize('body', [TimeoutError('timed out'), {'bad': []}, [], {'hits': None}])
def test_api_failures_report_to_stderr_without_fake_results(plugin, body, capsys):
    obj, rows, _, respond, _ = plugin
    respond([body])
    obj.search('example')
    assert not rows
    assert '1337x via Knaben:' in capsys.readouterr().err


def test_genuine_empty_results_do_not_report_failure(plugin, capsys):
    obj, rows, requests, respond, _ = plugin
    respond([{'hits': []}])
    obj.search('no match')
    assert not rows and len(requests) == 1
    assert not capsys.readouterr().err


def test_direct_search_stays_direct_and_empty_table_avoids_fallback(plugin, monkeypatch):
    obj, rows, requests, _, _ = plugin
    html = '''<tr><td class="coll-1 name"><a href="/torrent/1/Example/">Example</a>
    <td class="coll-2 seeds">5</td><td class="coll-3 leeches">1</td>
    <td class="coll-4 size">1 GB</td></tr>'''
    monkeypatch.setattr(obj, '_get', lambda *args, **kwargs: html)
    obj.search('example')
    assert len(rows) == 1 and rows[0]['name'] == 'Example'
    assert rows[0]['link'].startswith(obj.url + '/torrent/')
    rows.clear()
    monkeypatch.setattr(obj, '_get', lambda *args, **kwargs: '<table class="table-list"></table>')
    obj.search('no match')
    assert not rows and not requests


def test_direct_probe_time_budget_leaves_time_for_api(plugin, monkeypatch):
    obj, rows, _, respond, module = plugin
    ticks = iter([0, 0, 3, 6])
    monkeypatch.setattr(module.time, 'monotonic', lambda: next(ticks))
    probes = []
    monkeypatch.setattr(obj, '_get', lambda url, timeout: probes.append(timeout) or '')
    respond([{'hits': [hit()]}])
    obj.search('example')
    assert probes == [3, 3] and len(rows) == 1


def test_download_passes_magnet_through_without_http(plugin, capsys):
    obj, _, requests, _, _ = plugin
    magnet = 'magnet:?xt=urn:btih:' + HASH
    obj.download_torrent(magnet)
    assert capsys.readouterr().out.startswith(magnet + ' ')
    assert not requests


def test_bad_detail_date_and_counts_cannot_break_other_results(plugin):
    obj, rows, _, respond, _ = plugin
    respond([{'hits': [hit(details='https://[broken', date='bad', bytes='bad',
                           liveSeeders='bad', livePeers=None, peers=None)]}])
    obj.search('example')
    assert len(rows) == 1
    assert rows[0]['pub_date'] == rows[0]['size'] == rows[0]['seeds'] == rows[0]['leech'] == -1
    assert rows[0]['desc_link'].startswith('https://knaben.org/search/')


def test_empty_or_unknown_category_does_not_request(plugin):
    obj, rows, requests, _, _ = plugin
    obj.search('')
    obj.search('example', 'unsupported')
    assert not rows and not requests
