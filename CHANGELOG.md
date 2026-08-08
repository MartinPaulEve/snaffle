## 1.1.0 (2026-08-08)

### Feat

- print the SSO login URL to stdout on institutional login
- institutional login for paywalled PDFs (browser + EZProxy)
- user-managed exclusions and a prune command
- search/download subcommands, saved manifest and --nuke
- discover the academic's ORCID instead of configuring it
- per-author OpenAlex work exclusions
- Okta push-to-device MFA for institutional login
- ORCID disambiguation for same-name authors
- add KCWorks repository, discover endpoints instead of configuring
- discover full text via Kagi search
- drop false-positive search hits by author matching
- block-pixel banner with cyan-to-green gradient
- public search and download plugins
- orchestration pipeline and Click CLI with banner
- plugin interfaces, auto-discovery and shared services
- core data model, dedupe, output layout and bibliography

### Fix

- EZProxy url= bases, visible browser, robust PDF resolution
- percent-encode URLs before fetching
- do not create empty year folders for failed downloads
- use Kagi v1 search API (POST, Bearer auth)
- merge same-work records that carry different DOIs
- merge title-variant duplicates (subtitle present/absent)
- validate PDF magic bytes before saving a download
- skip Unpaywall unless a real email is configured
- skip JSTOR/Project MUSE search without a browser session
- make downloads actually work (OA path)
- make ORCID name resolution robust to messy records
- normalize DOI and demote Unpaywall

### Perf

- discovery stops at first working copy; validate PDFs
