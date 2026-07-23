---
name: chaoxing-quiz
description: Automate 超星学习通 (Chaoxing) quiz/exercise workflows with Playwright. Use this whenever the user shares a chaoxing.com/mooc1/mooc2 quiz, 随堂练习, 章节测验, 作业, or 考试 link and wants questions extracted, answers filled, selected-answer verification, progress/completion checks, or browser-workflow diagnosis. Leave final submission to the user by default; submit only after explicit, scoped user authorization and post-submit verification.
allowed-tools: Bash(playwright-cli:*)
---

# 超星学习通 Quiz Automation

Use this skill for Chaoxing/学习通 quiz pages. Prefer the shortest reliable path:

1. Attach to the user's real Chrome session.
2. Determine which page version is loaded from frames and DOM selectors.
3. Extract questions and options from the correct frame.
4. Fill answers by clicking the page's real option elements.
5. Verify selected answers from the DOM.
6. Stop before any final submit/交卷/确定 action and tell the user the page is ready for their manual submission.

For a whole-course request, execution is a stateful workflow, not a background wait. Report a concrete checkpoint at least every 30 seconds: active chapter, discovered quiz count, verified/submitted count, and whether the current delay is attaching, loading, observing, filling, or verifying. A command with no durable page-state change is diagnostic work, not progress.

Default final action: do not click `提交`, `交卷`, or a submission confirmation dialog. The user wants to submit manually after answers are filled and verified.

## Submission Boundary

Treat submission as an external side effect. Keep the manual-submit default unless the user explicitly authorizes submission for a defined scope, for example a named quiz or "all remaining chapter tests in this course".

When explicit authorization exists:

1. Verify every question has a selected value and compare the actual values with the intended answer map.
2. Click the visible `提交`/`交卷` control and inspect the confirmation dialog.
3. Confirm only after the dialog shows the expected quiz and no unanswered-question warning remains.
4. Verify the returned result state, score/result page, or task status before moving to the next task.
5. Never treat a click, a closed dialog, or a changed URL alone as proof of submission.

If the user has not authorized submission, hand off after step 1 and do not open a confirmation dialog.

## Session Control And Recovery

Use one browser-control path at a time. Do not drive the same Chrome tab concurrently with `playwright-cli`, a Chrome-extension browser bridge, and operating-system mouse/keyboard automation; each can steal focus or detach the other session.

### Preferred Control Path And Time Budget

For a user-owned logged-in Chrome, prefer the Playwright Chrome extension:

```powershell
playwright-cli -s=cx attach --extension=chrome
playwright-cli -s=cx tab-list
playwright-cli -s=cx snapshot --filename=initial.yml
```

Use CDP only when the extension cannot be installed or attached:

```powershell
playwright-cli -s=cx attach --cdp=chrome
```

Set a short budget for each control phase. Attach, tab discovery, and the first snapshot should each complete within roughly 30 seconds. If the same phase times out twice, stop retrying it, report the exact phase and last verified state, then switch once to the other supported path. Do not leave the user with a long silent sequence of retries.

After an attach succeeds, keep the session name and the current course URL in the progress record. Detach at the end:

```powershell
playwright-cli -s=cx detach
```

Before changing an answer, navigating a chapter, or submitting:

1. Take one fresh, narrow observation of the active quiz: frame URL/DOM snapshot for text workflows, or a screenshot when `font-cxsecret` garbles text.
2. Confirm the intended tab title and course URL. If the tab changed, reclaim/re-attach it before acting.
3. Use the page's real option element or a current DOM node ID. After the click, verify the selected state or hidden answer field.

On `Frame detached`, repeated browser timeouts, or a stale tab:

1. Stop repeated clicks immediately. The page may already have received the last action.
2. Reconnect to the same course tab and read the current selected state before retrying anything.
3. If the control path remains unstable after two recovery attempts, leave the course page intact, report the exact completed/unchecked scope, the failed phase, and the elapsed retry budget; then ask the user to restore a stable Chrome session or install/enable the extension.
4. Do not fall back to guessed screen coordinates. Display scaling, window movement, and concurrent browser control make coordinate clicks non-verifiable.

## Course-Level Completion Check

When the request covers a whole course rather than one link, inspect the course directory first and build a finite chapter checklist. For every chapter, record either `no quiz card found` or a quiz state: `not started`, `answers verified`, `submitted`, or `result verified`. A yellow/orange task counter only proves that some task exists; it does not prove that the chapter contains a quiz.

Do not declare the course complete until every discovered chapter-test task point has a verified terminal state. If the directory loads lazily, scroll/search it deliberately and record any section that could not be inspected instead of assuming there are no more tests.

### Fast Course Run Protocol

Use this order to avoid spending most of the session on unstable navigation or normal learning tasks:

1. Take one directory snapshot and list all chapters before answering. Preserve the checklist in the task notes or named snapshots.
2. Open a chapter and save a narrow snapshot. Search only for `章节测验`, `题量:`, `提交`, and completion state. If none are present, mark `no quiz card found` and move on without playing video, downloading resources, or clicking ordinary tasks.
3. When a quiz card is present, screenshot the card once. `font-cxsecret` often makes snapshot text unreadable while the rendered image is clear.
4. Resolve answers from the course text first; use rendered screenshots for ambiguous text/images. Do not infer a full answer map from garbled DOM strings alone.
5. Fill through real controls. For a multi-question card, a single `run-code` action may click all current DOM options, but it must return the question number and selected letter for every click. Then take one verification snapshot and require one selected value per question.
6. Submit only when authorized. Read the confirmation dialog, then the result page. Record the exact score and whether retry/rework is actually offered.

Do not count a chapter as completed merely because the sidebar count changed. Require `任务点已完成`, an explicit result state, or an equivalent verified terminal signal.

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

Prefer the extension attach above for an existing logged-in Chrome. It keeps the user-visible session and avoids relying on remote-debugging availability. Use this CDP command only as the fallback when the extension path is unavailable:

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

### Verify after fill

Do not trust the click count. Re-read active/selected option state or the page's answer summary.

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

### Manual submit handoff

After verification, stop here. Do not click the submit button. Report the selected-answer summary and tell the user they can manually click the page's `提交` button if everything looks right.

```javascript
async page => {
  const frame = page.frames().find(f => f.url().includes('answerQuestion') || f.name().includes('frame_content'));
  return await frame.evaluate(() => {
    const submitVisible = [...document.querySelectorAll('.submit-btn,.bottom-btn div,button')]
      .some(el => el.offsetParent !== null && el.innerText.trim() === '提交');
    return { status: 'ready_for_manual_submit', submitVisible };
  });
}
```

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

Do not spend a long session reverse-engineering the font before testing a rendered element screenshot. One screenshot of the actual quiz card is the fast default; font decoding is justified only when many answers cannot be resolved visually or from course text.

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

### Verify after fill

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

### Manual submit handoff

After hidden inputs match the expected answers, stop here. Do not click `.btnSubmit`, do not click the `确认提交？` dialog, and do not patch page functions to bypass dialogs. Report readiness for manual submission.

```javascript
async page => {
  const frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
  return await frame.evaluate(() => {
    const submitVisible = [...document.querySelectorAll('.btnSubmit,button,a')]
      .some(el => el.offsetParent !== null && /提交|交卷/.test(el.innerText || el.value || ''));
    return { status: 'ready_for_manual_submit', submitVisible };
  });
}
```

## Decision Notes From Local Runs

- The successful 随堂练习 run used Chrome attach plus a Vue-style `.question-item` page. Answers were selected by clicking options in `frame.evaluate`, then verified by reading the selected/my-answer state. Current workflow stops after this verification so the user can submit manually.
- The tested 章节测验 link used old nested frames and `doHomeWorkNew`. It had 20 `.TiMu.newTiMu` questions, 100 `.font-cxsecret` nodes, hidden answer inputs, and old submit functions (`btnBlueSubmit`, `workPop`, `validateTimeNew`).
- In the verified Android 章节测验 closed loop, `font_decoder_full.js` decoded the old page successfully (`decoded 89 characters, replaced in 100 elements`). Hidden inputs matched all 20 selected answers before submission. Current workflow stops there and leaves `.btnSubmit` / confirmation dialogs untouched.
- Therefore: keep both fill-and-verify workflows, but leave final submission to the user.

## Common Pitfalls

- **Node assertion/CSPRNG error is not necessarily nvm**: if `node -e "console.log('ok')"` works in the user's terminal but Codex Playwright fails, the running Codex process may be missing `SystemRoot`/`WINDIR`.
- **Chrome CDP attach may need a user toggle**: `chrome://inspect/#remote-debugging` -> allow remote debugging.
- **Frame names are not stable**: `frame_content`, `frame_content-hd`, and unnamed child frames all appear. Prefer URL plus DOM selector detection.
- **Vue pages do not need hidden-input manipulation**: click `li` elements and let Vue update internal state.
- **Old pages do use hidden inputs**: after clicking `.Zy_ulTop li`, verify `input[id^=answer]`.
- **DOM text may be garbled on old pages**: `font-cxsecret` affects extraction, not the visual browser rendering.
- **Image downloads may fail with 403**: screenshot the rendered image element in the logged-in browser.
- **Manual final submission**: after filling, compare expected answers against DOM-selected/hidden values, then stop and tell the user the page is ready. Do not click final submit/交卷/确认 controls.
- **Slow runs with no visible result**: classify every wait as `attach`, `load`, `observe`, `fill`, `submit`, or `verify`. After two failures in the same classification, change control path or stop with a precise handoff; do not convert a timeout into silent repeated attempts.
- **Stale snapshot refs**: Chaoxing replaces iframe content and generated references after navigation. Re-snapshot after each chapter change; never reuse an old ref just because its text label looks familiar.
- **Low score without retake**: treat `任务点已完成`, score, and retry availability as three distinct facts. Report the exact score and lack of retry instead of claiming the quiz is fully correct.

## Reference Scripts

- `references/chaoxing_quiz_answer.js`: old-page answer script template. It contains hardcoded sample answers, fills and verifies only, and should be edited per quiz before use.
- `references/font_decoder_full.js`: old-page `font-cxsecret` decoder using Typr.js and OCS font table.
- `references/font_decoder.js`: notes and helpers for font/image handling.
- `references/typr_core.js`: bundled Typr.js parser used by the decoder.
