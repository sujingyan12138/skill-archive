# Pitfalls And Debugging

## High-Value Pitfalls From The Douyin Favorites Project

### 1. Packaging success is not runtime success

PyInstaller can finish successfully while the EXE still fails at runtime.

Typical symptoms:

- EXE launches but browser automation fails
- imported modules are missing only after packaging
- config or output paths behave differently than source runs

Always run the packaged EXE end to end.

### 2. Dynamic Selenium modules may be omitted

The Douyin project failed after packaging with:

`No module named 'selenium.webdriver.edge.webdriver'`

Root cause:

- PyInstaller did not collect the needed Selenium submodules

Fix pattern:

- add hidden imports
- for broad Selenium use, `collect_submodules("selenium")` is often safer than adding one module at a time

This applies to many browser-automation libraries with dynamic imports.

### 3. Browser login and HTTP download should be separate concerns

A reliable pattern is:

1. Use Selenium only to obtain authenticated state
2. Use `requests.Session()` for API calls and downloads

Benefits:

- easier retries
- faster downloads
- simpler logging
- less browser fragility

### 4. Auth acquisition can fail for multiple reasons

When automatic cookie retrieval fails, consider:

- the user is not logged in on the target site
- browser profile encryption blocks cookie access
- the active login is not in the default browser profile
- the process is running under a different Windows user
- browser automation launches but session validation is wrong

Always offer a fallback path:

- manual cookie paste
- manual target ID input

### 5. Sites often need browser-like headers for media downloads

If JSON APIs work but media downloads fail, inspect:

- `User-Agent`
- `Referer`
- `Range`
- media-specific fetch headers

Video endpoints often behave differently from metadata endpoints.

### 6. Runtime path bugs show up after packaging

If the tool writes `config.json` or downloads into unexpected locations, the likely issue is using relative paths without a stable application directory.

Design paths explicitly before packaging.

### 7. Old build dependencies can break modern packaging

The Douyin project hit a PyInstaller failure because `setuptools` was too old for the active environment.

Fix pattern:

- keep a dedicated build requirements file
- upgrade build-time tooling explicitly

Example:

```powershell
python -m pip install --upgrade -r requirements-build.txt
```

### 8. Parallel status checks can lie during Git operations

If you switch branches and inspect status in parallel, the status snapshot may reflect the old branch.

After branch-changing commands, run a final explicit check:

- `git branch --show-current`
- `git status --short --branch`

## Debugging Order

When a crawler or packaged EXE fails, debug in this order:

1. Is the business logic reached?
2. Is authentication valid?
3. Is the endpoint response what the parser expects?
4. Are runtime paths correct?
5. Is this a packaging-only missing dependency?
6. Is a local environment or proxy issue blocking network access?

## Pre-Release Sanity Checklist

- source version runs successfully
- login flow succeeds
- sample downloads succeed
- rerun proves resume/dedup works
- packaged EXE runs successfully
- dynamic browser modules are present
- config and outputs land in expected directories
- release artifact is prepared separately from source history
