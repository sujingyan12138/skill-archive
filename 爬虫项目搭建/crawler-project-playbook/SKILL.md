---
name: crawler-project-playbook
description: Reusable workflow for building and shipping crawler projects that log in to websites, capture cookies or authenticated API traffic, download media or structured data, package the tool, and publish it. Use when Codex needs to plan or implement a new crawling/downloading project, especially browser-assisted crawlers, authenticated crawlers, Windows-first tools, or projects that may later be distributed as an EXE.
---

# Crawler Project Playbook

Use this skill to turn a crawler idea into a maintainable project, not just a one-off script.

Follow this sequence:

1. Clarify the target
2. Choose the acquisition path
3. Design the runtime layout
4. Implement the crawler
5. Add resilience
6. Verify with real runs
7. Package only after runtime is stable
8. Prepare repository and release flow

## 1. Clarify The Target

Capture these decisions before writing code:

- What is being collected: media, JSON data, HTML fields, documents, or a mix
- Whether login is required
- Whether the site has a visible API after login
- Whether the output is a one-time export or a reusable end-user tool
- Whether the user will run source code or a packaged executable
- Where files should be stored on disk

If authentication is involved, prefer solving login and session acquisition first. For many crawler projects, the real blocker is not parsing; it is obtaining a stable authenticated context.

## 2. Choose The Acquisition Path

Use the simplest reliable path that works.

Decision order:

1. Direct authenticated HTTP requests
2. Reuse browser cookies from an installed browser
3. Launch a real browser with Selenium or Playwright and let the user log in
4. Intercept network traffic only if simpler paths fail

Prefer browser-assisted login when:

- The site uses modern anti-bot checks
- Cookie extraction from the browser is unreliable
- The user can log in manually but the script needs to reuse that session

Prefer direct requests after login when:

- The site exposes a stable JSON API
- Downloads are easier and faster through `requests`
- The browser is only needed to obtain cookies or IDs

## 3. Design The Runtime Layout

Before implementation, make runtime paths explicit.

Always decide:

- Where config is read from
- Where outputs are written to
- Whether the program must behave correctly after EXE packaging

For source code, `__file__`-relative paths may be enough. For packaged apps, define an application directory and keep config/output relative to it.

Read `references/runtime-and-packaging.md` when the crawler may later be packaged or shared with non-technical users.

## 4. Implement The Crawler

Build in this order:

1. Config loading
2. Authentication acquisition
3. Target discovery
4. Data parsing
5. Download pipeline
6. Resume or dedup logic

Recommended implementation patterns:

- Keep HTTP logic in a session object
- Separate config/auth helpers from download logic
- Normalize filenames early
- Persist resume state with simple logs or manifests
- Add explicit headers for media downloads when the site expects browser-like requests

If the site offers multiple endpoints, try them as a fallback chain instead of assuming one endpoint will survive.

## 5. Add Resilience

Most crawler pain comes from edge cases, not the happy path.

Add these guardrails by default:

- Timeout on every request
- Retry for transient failures
- Backup URLs for media downloads when available
- Rate limiting or short sleeps between high-risk requests
- Detection for empty pages or missing payloads
- Safe filename cleaning for Windows
- Skip-already-downloaded checks

Read `references/pitfalls-and-debugging.md` when a crawler works inconsistently, passes in source form but fails after packaging, or depends on Selenium/browser modules.

## 6. Verify With Real Runs

Do not trust a crawler until real data has flowed through it.

Minimum verification:

- Run the login flow end to end
- Confirm the authenticated request actually returns expected payloads
- Download a small real sample
- Verify output layout on disk
- Re-run to confirm dedup/resume works

For media projects, verify both content types separately if the site mixes images, videos, covers, or metadata.

## 7. Package Only After Runtime Is Stable

Do not start with packaging. First make the Python version reliable.

When packaging:

- Add a dedicated build dependency file
- Add a repeatable build script
- Commit the PyInstaller `.spec` if it contains real project knowledge
- Test the built EXE, not just the Python entrypoint

Treat these as separate questions:

- Does the project build?
- Does the built EXE run?
- Does the EXE still contain every dynamic dependency?

If Selenium, browser helpers, or other dynamically imported libraries are involved, expect hidden imports to be necessary.

## 8. Prepare Repository And Release Flow

For shareable crawler tools:

- Commit source, build scripts, and packaging rules
- Do not commit large binary outputs into Git by default
- Publish EXE files via GitHub Release instead of normal source history
- Keep development on a feature branch, then fast-forward or merge into the stable branch

When network access fails during Git or package installs, try the user's local proxy before assuming the remote service is down.

## Core Heuristics

- Solve authentication before parsing
- Prefer the simplest stable acquisition path
- Design runtime paths before packaging
- Separate browser login from HTTP downloading when possible
- Validate with real runs before polishing
- Treat packaging as a second engineering problem, not a final checkbox

## Use The References

- Read `references/runtime-and-packaging.md` for path design, EXE packaging, `.spec` strategy, and release guidance.
- Read `references/pitfalls-and-debugging.md` for concrete failure modes distilled from the Douyin favorites crawler project.
