---
name: chaoxing-quiz
description: Automate 超星学习通 (Chaoxing) quiz/exercise workflows with Playwright. Use this whenever the user shares a chaoxing.com/mooc1/mooc2 quiz, 随堂练习, 章节测验, 作业, or 考试 link and wants questions extracted, answers filled, submission verified, or the page/debugging workflow diagnosed.
allowed-tools: Bash(playwright-cli:*)
---

# 超星学习通 Quiz Automation

Use this skill for Chaoxing/学习通 quiz pages. Prefer the shortest reliable path:

1. Attach to the user's real Chrome session.
2. Determine which page version is loaded from frames and DOM selectors.
3. Extract questions and options from the correct frame.
4. Fill answers by clicking the page's real option elements.
5. Verify selected answers from the DOM before submitting.
6. Submit only when the user asked to complete/submit, then verify the post-submit state.

Do not assume all Chaoxing pages share one implementation. The main split is:

- **新版 Vue 随堂练习**: usually `mooc2-ans.chaoxing.com`, `.question-item`, `.option-list`, direct submit button.
- **旧版章节测验/作业**: usually `mooc1.chaoxing.com/.../studentstudy`, nested frames, final URL contains `doHomeWorkNew`, DOM uses `.TiMu.newTiMu`, `.Zy_ulTop`, often `font-cxsecret`.

## Environment Setup

### Windows/Codex Node pitfall

If `playwright-cli` or Node fails with assertion/CSPRNG/native module errors, first check whether the current Codex process is missing Windows environment variables. In this session the system Node was fine, but Codex did not inherit `SystemRoot`/`WINDIR`; setting them fixed Playwright.

PowerShell prefix:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'; playwright-cli list
```

Use the same prefix for every `playwright-cli` command in the current Codex process if needed. Setting machine/user env vars helps future terminals, but the already-running Codex process may still need the prefix until restarted.

### Attach to the user's Chrome

Prefer attaching to the existing Chrome so Chaoxing login state and rendered resources are available.

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'; playwright-cli -s=cx attach --cdp=chrome
```

If Chrome refuses CDP attach, open `chrome://inspect/#remote-debugging` in Chrome and enable **Allow remote debugging for this browser instance**, then retry. This is often simpler than relaunching Chrome with a debugging port.

For a new isolated browser only:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'; playwright-cli -s=cx open --browser=chrome --persistent
```

Quote Chaoxing URLs in PowerShell because they contain `&`.

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'; playwright-cli -s=cx goto "https://..."
```

## First Diagnostic Step

Always inspect frames before writing page-specific code:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'; playwright-cli -s=cx run-code "async page => page.frames().map((f,i)=>({i,name:f.name(),url:f.url().slice(0,180)}))"
```

Then inspect the active quiz frame:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'; playwright-cli -s=cx run-code "async page => {
  const f = page.frames().find(fr =>
    fr.url().includes('answerQuestion') ||
    fr.url().includes('doHomeWorkNew') ||
    fr.name().includes('frame_content')
  );
  if (!f) return { error: 'no quiz-like frame', frames: page.frames().map(fr => ({name: fr.name(), url: fr.url()})) };
  return await f.evaluate(() => ({
    url: location.href,
    title: document.title,
    text: document.body.innerText.slice(0, 1000),
    vueQuestionCount: document.querySelectorAll('.question-item').length,
    oldQuestionCount: document.querySelectorAll('.TiMu.newTiMu, .TiMu').length,
    secretFontCount: document.querySelectorAll('.font-cxsecret').length,
    hasSubmitBtn: !!document.querySelector('.submit-btn,.btnSubmit')
  }));
}"
```

Use the result to choose the workflow below.

## Workflow A: 新版 Vue 随堂练习

Observed shape:

```text
mooc2-ans.chaoxing.com/.../mycourse/stu
  iframe / page with quiz content
    .question-item
      .question-name
      .option-list li
        .option-letter
```

Do not rely on a single frame name. Some pages use `frame_content`, some use `frame_content-hd`; select by DOM.

### Extract questions

```javascript
async page => {
  const frame = page.frames().find(f =>
    f.url().includes('answerQuestion') ||
    f.name().includes('frame_content') ||
    f.url().includes('stu')
  );
  return await frame.evaluate(() => [...document.querySelectorAll('.question-item')].map((q, i) => ({
    index: i + 1,
    type: q.querySelector('.grey-text')?.innerText.trim() || '',
    title: q.querySelector('.question-name')?.innerText.replace(/\s+/g, ' ').trim() || '',
    options: [...q.querySelectorAll('.option-list li')].map(li => ({
      letter: li.querySelector('.option-letter')?.innerText.trim() || '',
      text: li.innerText.replace(/\s+/g, ' ').trim()
    }))
  })));
}
```

### Fill answers

Use real clicks on the `li` elements so Vue state updates. Do not set classes or hidden fields manually.

```javascript
async page => {
  const answers = {
    1: 'B',
    2: 'D',
    21: '2' // 判断题 may be represented as option index/text; inspect page first
  };

  let frame = page.frames().find(f => f.url().includes('answerQuestion'));
  if (!frame) {
    for (const f of page.frames()) {
      const hasVueQuestions = await f.evaluate(() => !!document.querySelector('.question-item')).catch(() => false);
      if (hasVueQuestions) { frame = f; break; }
    }
  }
  if (!frame) return 'No Vue question frame found';

  return await frame.evaluate(async (answers) => {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    const items = [...document.querySelectorAll('.question-item')];
    const clicked = [];

    for (let i = 0; i < items.length; i++) {
      const wanted = answers[i + 1];
      if (!wanted) continue;
      const targets = String(wanted).split('');
      const lis = [...items[i].querySelectorAll('.option-list li')];
      for (const li of lis) {
        const letter = li.querySelector('.option-letter')?.innerText.trim();
        const text = li.innerText.trim();
        if (targets.includes(letter) || targets.includes(String(lis.indexOf(li) + 1)) || targets.some(t => text.includes(t))) {
          li.click();
          clicked.push(`${i + 1}:${letter || lis.indexOf(li) + 1}`);
          await sleep(60);
        }
      }
    }
    return clicked;
  }, answers);
}
```

### Verify before submit

Do not trust the click count. Re-read active/selected option state or the page's answer summary. On submitted Vue exercises, Chaoxing may show `我的答案：...`.

```javascript
async page => {
  const frame = page.frames().find(f => f.url().includes('answerQuestion') || f.name().includes('frame_content'));
  return await frame.evaluate(() => [...document.querySelectorAll('.question-item')].map((q, i) => {
    const selected = [...q.querySelectorAll('.option-list li')]
      .filter(li => /active|selected|checked|on/.test(li.className) || li.getAttribute('aria-checked') === 'true')
      .map(li => li.querySelector('.option-letter')?.innerText.trim() || li.innerText.trim().slice(0, 10));
    const mine = q.innerText.match(/我的答案[:：]\s*([A-Z0-9]+)/)?.[1];
    return { index: i + 1, selected, mine };
  }));
}
```

### Submit

For Vue 随堂练习, direct click is usually enough. There is normally no need to patch `confirm`, `workPop`, `validateTimeNew`, or AJAX.

```javascript
async page => {
  const frame = page.frames().find(f => f.url().includes('answerQuestion') || f.name().includes('frame_content'));
  await frame.evaluate(() => {
    const btn = [...document.querySelectorAll('.submit-btn,.bottom-btn div,button')]
      .find(el => el.innerText.trim() === '提交');
    btn?.click();
  });
  await page.waitForTimeout(1500);
  return await frame.evaluate(() => document.body.innerText.includes('已提交') || document.body.innerText.includes('我的答案'));
}
```

Known success text: `已提交，待教师公布正确答案`. This means success even if no score appears immediately.

## Workflow B: 旧版章节测验/作业

Observed shape:

```text
mooc1.chaoxing.com/mycourse/studentstudy
  iframe[name=iframe] -> /knowledge/cards
    child iframe -> /ananas/modules/work/index.html
      iframe[name=frame_content] -> /work/doHomeWorkNew
```

Final quiz frame selector:

```javascript
const frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
```

DOM:

```text
.TiMu.newTiMu
  .Zy_TItle
  .font-cxsecret
  .Zy_ulTop li[onclick*="addChoice"][qid][qtype]
    .num_option[data="A"]
  input[id^=answer]
  input[id^=answertype]
```

### Extract structure

```javascript
async page => {
  const frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
  return await frame.evaluate(() => [...document.querySelectorAll('.TiMu.newTiMu, .TiMu')].map((q, i) => ({
    index: i + 1,
    qid: q.querySelector('[id^="answer"]')?.id?.replace('answer', '') || q.querySelector('[qid]')?.getAttribute('qid') || '',
    qtype: q.querySelector('[id^="answertype"]')?.value || q.querySelector('[qtype]')?.getAttribute('qtype') || '',
    title: q.querySelector('.Zy_TItle')?.innerText.replace(/\s+/g, ' ').trim() || '',
    options: [...q.querySelectorAll('.Zy_ulTop li')].map(li => ({
      letter: li.querySelector('[data]')?.getAttribute('data') || '',
      text: li.innerText.replace(/\s+/g, ' ').trim(),
      hasImage: !!li.querySelector('img')
    }))
  })));
}
```

### font-cxsecret

旧版页面 often renders correct Chinese visually but returns garbled DOM text. Do not waste time decoding fonts unless the DOM text is needed for reasoning/search.

Practical options, in order:

1. If the browser view is readable and only a few questions are ambiguous, take screenshots of the rendered question/option elements and inspect the image.
2. If many questions need text extraction, run the bundled decoder or improve it first.
3. If only option letters are needed because the answer key is known, skip decoding.

Bundled files:

- `references/font_decoder_full.js`
- `references/typr_core.js`
- `references/font_decoder.js`

Local note: `font_decoder_full.js` now uses this skill folder's absolute `typr_core.js` path for the current machine. If the skill is copied elsewhere, update that one path.

### Image options

Chaoxing image URLs, especially `p.cldisk.com`, may return `403 Forbidden` when downloaded directly because the request lacks browser cookies/referer. Use Playwright element screenshots instead:

```javascript
async page => {
  const frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
  const img = await frame.locator('.Zy_ulTop li img').first();
  await img.screenshot({ path: 'chaoxing-option.png' });
  return 'saved chaoxing-option.png';
}
```

### Fill answers

Click the real `li`; this calls Chaoxing's `addChoice(this)` and updates hidden answers.

```javascript
async page => {
  const answers = { 1: 'D', 2: 'A' };
  const frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
  return await frame.evaluate((answers) => {
    const result = [];
    const qs = [...document.querySelectorAll('.TiMu.newTiMu, .TiMu')];
    qs.forEach((q, idx) => {
      const wanted = answers[idx + 1];
      if (!wanted) return;
      for (const li of q.querySelectorAll('.Zy_ulTop li')) {
        const letter = li.querySelector('[data]')?.getAttribute('data');
        if (letter && String(wanted).includes(letter)) {
          li.click();
          result.push(`${idx + 1}:${letter}`);
        }
      }
    });
    return result;
  }, answers);
}
```

### Verify before submit

Old pages usually store answers in hidden inputs. Verify those, not just CSS classes.

```javascript
async page => {
  const frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
  return await frame.evaluate(() => [...document.querySelectorAll('.TiMu.newTiMu, .TiMu')].map((q, i) => {
    const input = q.querySelector('input[id^="answer"], input[name^="answer"]');
    return { index: i + 1, value: input?.value || '' };
  }));
}
```

### Submit

Start simple:

```javascript
async page => {
  const frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
  await frame.locator('.btnSubmit').click();
  await page.waitForTimeout(1000);
  return await frame.evaluate(() => document.body.innerText.slice(-1000));
}
```

If the custom dialog blocks submission, click the visible confirm button in the dialog. Only use function patching as a fallback when direct UI interaction is unreliable.

In the verified old 章节测验 flow, this was sufficient:

1. Click `.btnSubmit`.
2. Wait for the visible alert dialog with text `确认提交？`.
3. Click the visible button whose accessible name is `确定` and text is `提交`.
4. Verify the final frame URL contains `selectWorkQuestionYiPiYue` or the page text contains `已完成` / `本次成绩`.

Example:

```powershell
$env:SystemRoot='C:\Windows'; $env:WINDIR='C:\Windows'; playwright-cli -s=cx click <确定按钮ref>
```

Fallback patch for old pages:

```javascript
async page => {
  const frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
  await frame.evaluate(() => {
    if (typeof $ !== 'undefined' && $.ajaxSetup) $.ajaxSetup({ async: false });
    window.confirm = () => true;
    window.alert = () => {};
    if (typeof validateTimeNew !== 'undefined') {
      validateTimeNew = function(a, b, c, cb) { if (typeof cb === 'function') cb('', ''); };
    }
    if (typeof workPop !== 'undefined') {
      workPop = function(tip, okText, cancelText, okCb) { if (typeof okCb === 'function') okCb(); };
    }
    if (typeof reqLimit !== 'undefined') reqLimit = 10;
    if (typeof submitLock !== 'undefined') submitLock = 0;
    if (typeof btnBlueSubmit === 'function') btnBlueSubmit();
  });
  await page.waitForTimeout(3000);
  return await frame.evaluate(() => document.body.innerText.slice(-1500));
}
```

Treat this patch as old-page emergency tooling, not the default path. It is unnecessary for the Vue 随堂练习 pages that submit correctly with a button click.

## Decision Notes From Local Runs

- The successful 随堂练习 run used Chrome attach plus a Vue-style `.question-item` page. Answers were selected by clicking options in `frame.evaluate`, then verified by reading the selected/my-answer state. Submit changed the page to `已提交，待教师公布正确答案`.
- The tested 章节测验 link used old nested frames and `doHomeWorkNew`. It had 20 `.TiMu.newTiMu` questions, 100 `.font-cxsecret` nodes, hidden answer inputs, and old submit functions (`btnBlueSubmit`, `workPop`, `validateTimeNew`).
- In the verified Android 章节测验 closed loop, `font_decoder_full.js` decoded the old page successfully (`decoded 89 characters, replaced in 100 elements`). Hidden inputs matched all 20 selected answers before submission, direct `.btnSubmit` opened a visible custom `确认提交？` dialog, clicking the visible `确定` button completed the work, and the result page showed `已完成` / `本次成绩100分`.
- Therefore: keep both workflows, but do not make the old submit patch/font decoder mandatory. Detect first, then use the simplest branch.

## Common Pitfalls

- **Node assertion/CSPRNG error is not necessarily nvm**: if `node -e "console.log('ok')"` works in the user's terminal but Codex Playwright fails, the running Codex process may be missing `SystemRoot`/`WINDIR`.
- **Chrome CDP attach may need a user toggle**: `chrome://inspect/#remote-debugging` -> allow remote debugging.
- **Frame names are not stable**: `frame_content`, `frame_content-hd`, and unnamed child frames all appear. Prefer URL plus DOM selector detection.
- **Vue pages do not need hidden-input manipulation**: click `li` elements and let Vue update internal state.
- **Old pages do use hidden inputs**: after clicking `.Zy_ulTop li`, verify `input[id^=answer]`.
- **DOM text may be garbled on old pages**: `font-cxsecret` affects extraction, not the visual browser rendering.
- **Image downloads may fail with 403**: screenshot the rendered image element in the logged-in browser.
- **Submit result wording differs**: 随堂练习 may show `已提交，待教师公布正确答案`; old work pages may show score/status/navigation.
- **Do not submit blindly**: after filling, compare expected answers against DOM-selected/hidden values. Submit after the user requested completion or after explicit confirmation if the prompt only asked to inspect.

## Reference Scripts

- `references/chaoxing_quiz_answer.js`: old-page answer script template. It contains hardcoded sample answers, defaults to `AUTO_SUBMIT = false`, and should be edited per quiz before use.
- `references/font_decoder_full.js`: old-page `font-cxsecret` decoder using Typr.js and OCS font table.
- `references/font_decoder.js`: notes and helpers for font/image handling.
- `references/typr_core.js`: bundled Typr.js parser used by the decoder.
