# Knaben's 1337x coverage: October 29, 2026

## Conclusion

Knaben is a practical indirect source for some 1337x results. Its API v2
supports server-side source filtering (`t=1337x`), and recent source-labelled
entries contain magnets and hashes, avoiding a request to a challenged 1337x
detail page. It is not established as a complete replacement for the original
catalogue. The original site's current challenge prevents a direct completeness
comparison.

The initial investigation was read-only. No application code, installed
plugins, settings, DNS configuration or services changed. Only this report was
added to the repository. No payload downloads or peer transfers were started.

## Method

- Examined the current `qbt_plugins/knaben.py` request and output handling.
- Read Knaben's API v1/v2 documentation and called the documented endpoints.
- Tested v2 source filtering for Ubuntu, Debian, Batman, Dune, Naruto and Python.
- Compared default, `dead` and `unsafe` flags separately, using bounded samples.
- Reproduced the current v1 plugin's two 300-result pages for four queries.
- Checked API-returned magnet hashes against each entry's `hash` field.
- Fetched two legacy Knaben proxy-only links to test their response status.

Public JSON responses are preserved in the session's temporary directory,
`qbt-knaben-coverage-20261029`. Timings are observed request times from this PC,
not service guarantees. Counts are an API snapshot and can change.

## Source-filtered search results

All rows below use `t=1337x`, without enabling `unsafe` or adult content.
The second column uses default filters. The third additionally passes `dead`,
which permits entries whose source-reported `seeders` field is zero.

| Query | Default total | Total with `dead` | Magnets in the latter result set |
|---|---:|---:|---:|
| Ubuntu | 0 | 0 | 0 |
| Batman | 1 | 21 | 21 |
| Naruto | 0 | 1 | 1 |
| Python | 2 | 35 | 35 |

Debian and Dune also returned zero with default filters; their `dead` variants
were not tested. Targeted searches generally answered in 0.4–1.0 seconds.

All Batman/Naruto/Python magnets in the `dead` samples carried the same BTIH
hash as their API entry. This checks internal consistency; it does not prove
the original publisher's identity or that the payload is available.

## Freshness and peer-count discrepancy

Browsing only 1337x returned:

| Filters | API total | Rows inspected | Rows with matching magnet/hash |
|---|---:|---:|---:|
| Default | 864 | 100 | 100 |
| Add `dead`, retain safety filtering | At least 10,000 | 100 | 100 |

The API reports a `gte` relation at 10,000, so this is a lower bound, not an
exact catalogue size. The newest entries in the latter sample were dated
October 29 in America/Phoenix, with recent `lastSeen` timestamps. These are
Knaben's reported timestamps, not independently verified upload times.

Of the 100 latest entries with `dead` allowed, 99 had `seeders=0`, while 93 had
positive `liveSeeders`. All 21 Batman, the one Naruto and all 35 Python entries
in those samples had positive `liveSeeders`. The default dead filter therefore
excluded entries with positive live counts. These are API claims; actual peers
were not contacted. A future implementation should use live counts when present,
preserving an actual zero and falling back only when the live value is null.

## Safety filters and older coverage

Testing `unsafe` separately substantially expanded older matches: Ubuntu rose
from zero to 76, and Batman from one to 885. Knaben's v1 documentation explains
that its safety filter excludes very old results as well as entries with higher
virus scores. Therefore an entry excluded by this filter is not necessarily
confirmed malware, and the flag is not a direct measure of catalogue quality.

This investigation does not recommend silently enabling `unsafe`. Prefer the
ordinary safety filter and explain why older catalogue coverage is incomplete.

Only 16 of the 76 Ubuntu entries exposed a magnet; the rest relied on a Knaben
proxy download URL. Both tested proxy-only entries returned HTTP 500. A proxy
URL being present is insufficient evidence that a result can be downloaded.
Source detail links still point to 1337x and can encounter its browser challenge.

## What the existing general Knaben plugin surfaces

The current plugin uses API v1, queries all sources, sorts by source `seeders`,
fetches at most two pages, skips RuTracker and deduplicates by hash/link. Its
600-row API samples contained these 1337x-labelled entries before deduplication:

| Query | All-source rows fetched | 1337x-labelled rows |
|---|---:|---:|
| Ubuntu | 600 | 0 |
| Batman | 600 | 0 |
| Naruto | 600 | 0 |
| Python | 600 | 2 |

Other sources dominate that seed-sorted window. A matching torrent might also
be indexed under another source, so these figures do not measure total missing
content. They show that the existing Knaben plugin does not provide a dependable
1337x-specific view. It also displays source `seeders`/`peers` and ignores the
live equivalents.

## Recommended implementation direction

1. Use API v2 GET requests with explicit `t=1337x` for a clearly labelled
   **1337x via Knaben** fallback. Keep source attribution visible.
2. Allow API entries with zero source-reported seeders (`dead`), retain safety
   filtering, and display live peer counts when supplied. Document that this
   does not establish torrent availability.
3. Initially accept only valid direct magnets or known hashes. Avoid treating
   unverified legacy proxy URLs as working downloads.
4. Bound paging and request timeouts; validate schema, hashes and no-match
   responses. Avoid calling 1337x detail pages to resolve an already-known hash.
5. Deduplicate fallback results by info hash and keep a clear distinction
   between a direct 1337x result and Knaben's indexed copy.
6. Test category filters, freshness, duplicates, missing live counts and API
   failures before changing the production plugin.

A browser helper is unnecessary for the direct-magnet subset. Full catalogue
equivalence remains unproven. Implementation followed the initial investigation
and is described below.

## Implemented fallback

After the investigation, `leetx.py` v1.1 was updated to keep direct 1337x search
first and fall back to API v2 restricted to `t=1337x` when mirrors are unavailable.
Direct probes use a six-second scheduling budget and at most three seconds per
request. API requests use an eight-second timeout, with at most two 300-row pages.
These are socket/request bounds, not a hard wall-clock deadline for DNS or a
server that continues to send data slowly.

Fallback rows carry `[1337x via Knaben]` in their title. They sort by
`liveSeeders`, prefer live counts including zero, and fall back to source counts
only when live values are absent/null. `dead` is permitted; `unsafe` and `xxx`
remain off. Category mappings are sent to Knaben. Its source taxonomy can place
anime under movies or courses under Other; a zero category search can therefore
be valid even when an all-category search has results.

The engine accepts validated hexadecimal/base32 BTIH magnets or constructs a
magnet from a known valid hash. It rejects mismatched hashes, foreign source
rows and proxy-only entries; it deduplicates by canonical hash. API errors go
to stderr rather than appearing as fake search rows. Legitimate empty API
responses remain quiet. A direct site's recognised empty results table does
not trigger fallback. The installer now recognises `api.knaben.org` as an
operational fallback host for DNS checks. No extra engine or service is added.

The separate general Knaben plugin retains its original behaviour. This change
provides the source-specific fallback without changing that plugin's filters.

### Verification

All 61 offline tests passed, including 15 fallback tests covering direct search,
legitimate empty tables, source/category filters, timeout scheduling, API errors,
hash mismatch rejection, hex/base32 deduplication, paging limits, live zero/null
counts, proxy-only rejection and magnet handoff. `git diff --check` passed.

Live isolated `nova2.py` checks against the bundled qBittorrent framework:

| Query | Category | Results | Time |
|---|---|---:|---:|
| Batman | All | 20 | 2.1 s |
| Batman | Movies | 15 | 2.7 s |
| Batman | TV | 3 | 1.9 s |
| Naruto | All | 1 | 1.9 s |
| Python | All | 35 | 1.8 s |
| Python | Books | 6 | 1.3 s |
| Ubuntu | All | 0 | 1.3 s |
| zzqxvnonexistent | All | 0 | 1.4 s |

All nonempty results used direct magnets labelled `[1337x via Knaben]`, with no
stderr errors. The first three Batman results displayed live seeder counts
176, 75 and 62. The real `nova2dl.py` entry point returned a validated fallback
magnet without a network request. Naruto/Anime and Python/Software searches
returned clean zero results, consistent with the source category mappings noted
above. Counts are snapshots, rather than promised catalogue sizes.

A PyInstaller build installed successfully into a temporary profile with
isolated application-data directories, no dependency changes and no qBittorrent
restart. All 22 engines plus the update notice loaded; bundled local plugin
files matched the source bytes. The installed `leetx` passed the actual health
checker with 20 Batman results in 1.4 seconds. The user's real installed
qBittorrent, settings and torrents were unchanged. This was a local build/test,
not a published release.

## Sources

- [Knaben API versions](https://knaben.org/api/)
- [API v1 documentation](https://knaben.org/api/v1/)
- [API v2 documentation](https://knaben.org/api/v2/)
- [Example source-filtered search](https://api.knaben.org/v2/search?q=batman&t=1337x&s=100&o=seeders&dead)
- [Example source-filtered recent browse](https://api.knaben.org/v2/browse?t=1337x&s=100&o=date&dead)
