# Engine additions and revisit: October 29, 2026

Checks ran from this Windows PC using the installer's pinned qBittorrent nova3
framework in a temporary directory. The installed qBittorrent, its settings and
its torrents were left alone. Only search responses and small torrent metadata
files were downloaded; no torrent payloads or peer transfers were started.

## Added

| Engine | Approach | Live search evidence | Download evidence |
|---|---|---|---|
| Internet Archive | One advanced-search API request, title terms, 100 results maximum | Ubuntu: 100 in 1–2 s; Sherlock Holmes, books: 100 in 1–2 s | Sample Ubuntu and book torrents parsed as valid metainfo |
| LinuxTracker | New `/torrents/?q=...` scraper, two pages maximum | Ubuntu: 50 in 2.1 s; Fedora: 50 in 2.0 s | Ubuntu torrent's SHA-1 info hash exactly matches its search magnet |
| Tokyo Toshokan | Searchable `/rss.php?terms=...`, 200 entries maximum | Naruto: 135 with magnets across all categories; anime: 107 after dropping entries explicitly marked Non-English | Valid hex/base32 magnet hashes extracted from RSS; peer availability not tested |
| Public Domain Torrents | Search the small catalogue in one request; resolve full-size AVI torrent on selection | Night of the Living Dead: 1; Sherlock Holmes: 9; about 1.1–1.2 s | Download through nova2dl succeeded; parsed torrent names the expected AVI |

All four returned zero results without errors for `zzqxvnonexistent`. All four
are standard-library plugins, registered in the installer, GUI name map and
weekly health-check queries. The obsolete `tokyotoshokan.py` remains retired;
the replacement is named `tokyotosho.py` so cleanup cannot delete it.

Internet Archive's search can list a torrent that requires login. The initial
Ubuntu hit returned HTTP 401; its metadata showed `access-restricted-item=true`
and the `loggedin` collection. Both are now excluded in the API query and
checked again in returned documents. A public book torrent returned HTTP 500
once and succeeded on a repeat request. The API's item size is the total item
size, and may differ from the files included in its torrent. Search matches
titles, rather than full text. Peer counts are unavailable.

Tokyo Toshokan's feed took about 2–3 s initially. Repeated checks later produced
one 10 s timeout and one successful response at about 10 s. The plugin has an
explicit 10 s request timeout; the existing health checker retries failures.
The final check from the built installer's installed copy succeeded with 135
results in 5.1 s. This remains an intermittent upstream reliability limitation. Its all-category
search includes adult material, music, manga and other content. The anime
category selects the site's anime feed and drops explicitly Non-English rows.

Public Domain Torrents reports unknown size and peer counts during search.
The full-size AVI link is resolved only when selected, avoiding one request per
search result. Its catalogue is small and old; valid torrent metadata does not
establish that every film currently has seeders.

## Revisited but not added

| Engine | Route checked | Finding |
|---|---|---|
| bt.etree.org | HTML search and `/rss/bt_etree_org.rdf` | HTML search still returns 403. RSS works, but known-title and nonsense query parameters return the same feed. Recent uploads alone are not a catalogue search, so it was not added. |
| TorrentClaw | JSON `/api/v1/search` and Torznab API | JSON search now answers anonymously, but explicitly withholds hashes, magnets and torrent downloads without a free account/API key. Torznab returns 401. Still unsuitable for the install-everything-without-configuration design. |
| EXT | HTML search and `/rss/?q=ubuntu` | Both return 403. |
| UIndex | Search page | Returns 403. |
| AniDex | Search page | Returns 403. |
| TorLock | Candidate search RSS path | Returns 404; no working search feed established. |
| TorrentGalaxy | Original `.to` domain and current LightDestory plugin source | `.to` fails local DNS. Current plugin uses `.one`, already recorded as a TheRARBG duplicate; its unbounded pagination and sleeps remain unsuitable. No independent recovered source established. |

No DNS settings, credentials, challenge solvers or installed plugins were
changed. An accessible public API/feed was preferred when available. BitSearch
was deliberately not revisited because the existing project notes prohibit
re-adding its flagged redirecting destination.

## References

- [qBittorrent community plugin list](https://github.com/qbittorrent/search-plugins/wiki/Unofficial-search-plugins)
- [Internet Archive advanced search](https://archive.org/advancedsearch.php)
- [Existing Internet Archive plugin](https://github.com/OyunErbabi/qBittorrent-Internet-Archive-Search-Plugin) informed the candidate research; the bundled implementation is custom and bounds its own request.
- [LinuxTracker public search](https://linuxtracker.org/torrents/?q=ubuntu)
- [LinuxTracker RSS](https://rss.linuxtracker.org/feed.xml) is recent-only and was not used as a replacement for full search.
- [Tokyo Toshokan searchable feed](https://www.tokyotosho.info/rss.php?terms=naruto)
- [Public Domain Torrents catalogue](https://www.publicdomaintorrents.info/nshowcat.html?category=ALL)
- [TorrentClaw API documentation source](https://github.com/torrentclaw/torrentclaw-skill/blob/main/references/api-reference.md); live responses impose stricter download authentication than its anonymous-search documentation suggests.

## Verification

Offline tests cover API query constraints and restricted-item exclusion,
LinuxTracker paging bounds/deduplication/counts, RSS entity handling and empty
responses, catalogue matching and download resolution. Real `nova2.py
--capabilities` loads all four new engines; live searches and sample metadata
downloads were checked separately from the user's installation.

Final checks: `python -m pytest -q` passed all 46 tests, and `git diff --check`
passed. A PyInstaller build installed successfully into a temporary profile
with isolated `LOCALAPPDATA` and `APPDATA`, no restart and no dependency changes.
All 22 search engines plus the update-notice plugin loaded. All bundled local
plugin bytes matched the source files. The four additions then passed the
health check from that installation: Internet Archive 100 rows / 1.0 s,
LinuxTracker 50 / 3.2 s, Public Domain Torrents 1 / 1.1 s, Tokyo Toshokan
135 / 5.1 s. The build was a local smoke test, not a published release.
