# FOSS Torrents and TsukiHime: October 30, 2026

Both candidates passed isolated search checks and were added as custom bundled
plugins, including installer registration, GUI names and weekly health queries.
No installed qBittorrent configuration, real plugin directory or torrent payload
was changed. Torrent downloads below refer only to small metainfo files.

## FOSS Torrents

The public torrent feed contains 1,072 entries. The master announcement feed
contains 264 project entries, with links identifying distributions, software
and games. The plugin searches release titles and torrent filenames locally,
then uses the project feed for category filtering and description links. A
nonempty search costs two requests; a query with no catalogue matches costs one.

Whole-word matching prevents a query such as `0 A.D.` from matching unrelated
filenames simply because they contain the letters A and D. Results are capped
at 100 and deduplicated by direct torrent URL. Only HTTPS torrent URLs under
the site's `direct-files` path are accepted. Requests have an eight-second
timeout and feeds are limited to 2 MiB. Invalid feeds produce an error instead
of being treated as a healthy empty search.

| Query | Category | Results | Observed time |
|---|---|---:|---:|
| Blender | Software | 26 | 2.0 s |
| Ubuntu | Software | 36 | 1.8 s |
| 0 A.D. | Games | 7 | 1.9 s |
| Blender | Games | 0 | 1.8 s |
| zzqxvnonexistent | All | 0 | 1.4 s |

All 26 Blender filenames linked by magnets on its project page were present
in the torrent catalogue. The sampled Blender Windows MSI metainfo parsed
correctly, and its exact info hash matched the project's magnet:
`94f0bcd640fb2bf40c9340579d6c88d0ff7b1647`. A sampled 0 A.D. Windows metainfo
also parsed correctly, naming the expected installer. Neither payload was
downloaded or executed. The existing LinuxTracker engine returned zero Blender
results, so this adds software coverage beyond that Linux-oriented catalogue.

The feed supplies no torrent size or peer counts; these display as unknown.
This is a search of the site's published catalogue, not a promise of every
historical release. Complete coverage was checked for the sampled Blender
project only. For category searches, an unmapped project is skipped rather
than guessed; it remains eligible in All. No per-release HTTP requests are made.

## TsukiHime

The old community plugin already received names, hashes, sizes and dates in its
search response, but fetched every release detail separately for tracker
counts. Some detail responses omit `trackers`, causing a crash. The custom
plugin uses the documented search response directly, making one request and
returning at most 100 raw API entries before filtering. It does not depend on
tracker details or Python 3.12-only f-string syntax.

Only rows with English audio or subtitle tags and an explicit non-adult flag
are included. Entries without those language tags are skipped. Hashes, release
IDs and titles are validated; hashes are deduplicated case-insensitively. Size
and source timestamp come from the search response. Peer counts display as
unknown instead of summing potentially overlapping tracker counts.

| Query | Category | Results | Observed time |
|---|---|---:|---:|
| Naruto | Anime | 67 | 1.5 s |
| Frieren | All | 70 | 1.2 s |
| zzqxvnonexistent | All | 0 | 1.2 s |

The public search schema documents `q`, `limit` (maximum 100) and `offset`.
The plugin requests only the first 100 entries, uses an eight-second request
timeout and makes no per-result requests. One-character and empty searches
make no requests. API errors and invalid schemas remain visible as failures.
Magnets use validated hashes and DHT; tracker counts are not invented.

### Overlap sample

The same Naruto query was run through the existing Nyaa, Anime Tosho and nekoBT
plugins. They returned 1,000, 75 and 26 rows respectively, with 1,072 distinct
hashes across those result samples. Of TsukiHime's 67 English-tagged hashes:

- 41 were also present in the combined samples.
- 26 were absent from those samples.

This establishes additional surfaced results, not exclusive torrents or a
complete comparison of all underlying databases. The services share upstream
sources, and different ordering, pagination and language filters affect overlap.
Actual payload availability was not tested by contacting peers.

## Sources and reproducibility

- [FOSS torrent catalogue](https://fosstorrents.com/feed/torrents.xml)
- [FOSS project feed](https://fosstorrents.com/feed/rss.xml)
- [FOSS feed documentation](https://fosstorrents.com/feed/)
- [Blender project downloads](https://fosstorrents.com/softwares/blender/)
- [TsukiHime API docs](https://api.tsukihime.org/v1/docs)
- [TsukiHime public schema](https://api.tsukihime.org/v1/swagger.json)
- [Original community plugin](https://github.com/dominc8/qbittorrent-tsukihime-search-plugin)

Raw responses, isolated nova3 files, search output and sampled metainfo were
saved under the session's temporary `qbt-foss-tsuki-20261030` directory. Test
queries are recorded in `tools/health_check.py`. Counts and timings above are
snapshots from this PC, not service guarantees.

## Validation

`python -m pytest -q` passed all 74 tests; `git diff --check` passed. Tests cover
catalogue/category matching, short-word query precision, feed validation,
deduplication and result limits, source hash and ID validation, language/adult
filtering, missing tracker data, empty responses and API errors.

Repeated live checks returned Blender 26, Ubuntu/software 36, 0 A.D./games 7,
Naruto 67 and Frieren 70, without stderr errors. Both nonsense queries returned
zero. The actual `nova2dl.py` helper downloaded Blender's valid 29,556-byte
metainfo file; TsukiHime results supply validated direct magnets.

A PyInstaller build installed successfully into temporary application-data
directories with dependencies skipped and no qBittorrent restart. All 24 search
engines plus the update notice loaded, and every bundled local plugin matched
its source bytes. The two new engines were then checked from that installation
using the real health-check helper. This was a local verification build, not a
published release or installation into the user's qBittorrent.
