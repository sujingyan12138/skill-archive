---
name: docx-diagram-fastpath
description: Use this skill whenever the user asks to draw activity diagrams, sequence diagrams, UML/process diagrams, or other report figures and insert them into a Word `.docx` document. Especially use it when the user complains that drawing/inserting pictures into Word takes too long, asks to add multiple diagrams to a document, asks why there should be more than one diagram, or needs Chinese software-engineering course-report diagrams with text descriptions. This skill prevents slow rework by planning diagram count first, generating images in batches, inserting into a copy of the DOCX once, and doing only targeted verification.
---

# DOCX Diagram Fast Path

Use this skill to efficiently add UML/process diagrams and supporting descriptions to a Word report without spending excessive time on repeated document edits and render attempts.

## Core Lesson

The slow path is:

1. Draw one big diagram immediately.
2. Insert it into Word.
3. Discover the teacher/leader wants text descriptions or multiple diagrams.
4. Redraw and reinsert repeatedly.
5. Try expensive full-document render checks after every small change.

The fast path is:

1. Read the document structure and existing section style first.
2. Decide the diagram split and explanation text before drawing.
3. Generate all images in one batch.
4. Replace only the target section in a copied DOCX.
5. Do structural checks first, then one final render attempt if tooling exists.

## When Working On Chinese Software Engineering Reports

Common expectation:

- Do not provide only one large activity diagram if the system has multiple major use cases.
- Add prose before diagrams explaining what the activity diagram shows.
- Explain why diagrams are split, usually because one total diagram is too complex and hides use-case logic.
- Keep captions consistent with nearby sections, such as `图3.2.1 用户注册 / 登录活动图`.
- Match the style of adjacent sections. If `3.1 顺序图` has numbered subsections and descriptions, make `3.2 活动图` use the same pattern.

Good split for a system like KnoBrain:

- User registration/login activity diagram
- Knowledge Q&A and recommendation activity diagram
- Learning diary, knowledge graph, and review reminder activity diagram
- Admin backend management activity diagram

Avoid making a single huge diagram unless the document has only one simple workflow.

## Workflow

### 1. Inspect Before Editing

Read the DOCX structure before changing anything:

- Locate the real body heading, not the table of contents entry. For example, choose the later `3.2 活动图`, not the early `3.2 活动图\t4`.
- Find the next heading, such as `3.3 状态图`, so edits stay inside the target section.
- Count existing inline shapes and identify current pictures in the target section.
- Inspect adjacent sections to copy style and numbering.

Useful checks:

```python
from docx import Document
doc = Document("input.docx")
for i, p in enumerate(doc.paragraphs):
    t = p.text.strip()
    if t.startswith("3.1") or t.startswith("3.2") or t.startswith("3.3"):
        print(i, repr(t), "pics=", len(p._element.xpath(".//pic:pic")))
print("inline_shapes", len(doc.inline_shapes))
```

### 2. Plan The Section Before Drawing

Draft this structure first:

```text
3.2 活动图
活动图总说明：说明活动图的作用。
拆分理由：说明为什么不是只画一张。

1. [用例组]活动图
[文字描述]
图3.2.1 ...
[图片]

2. [用例组]活动图
[文字描述]
图3.2.2 ...
[图片]
```

Make the split match use cases, not arbitrary pages. Merge tightly coupled use cases when it improves clarity, such as:

- Knowledge Q&A + recommendation
- Diary + graph + reminder

### 3. Generate Diagrams As PNG First

For Word reports, PNG is usually the fastest reliable insert format.

Recommended diagram style:

- Use swimlanes for participant responsibility, such as `普通用户`, `KnoBrain系统`, `数据库 / 外部服务`, `管理员`.
- Keep the main success path visible.
- Put rare failure branches in the note under the diagram instead of drawing every loop.
- Use decision diamonds only for key decisions.
- Avoid long crossing lines; if lines become messy, split the diagram.
- Leave enough bottom margin. A diagram that looks okay standalone may be clipped after scaling into Word.

Practical sizing:

- Use wide images around `1800px` width.
- Keep height moderate:
  - simple diagrams: `900-1050px`
  - larger diagrams: `1100-1250px`
- Insert at about `6.2-6.5 inches` width in Word.

### 4. Edit A Copy, Not The Original

Always preserve the original DOCX unless the user explicitly asks to overwrite it.

Recommended output name:

```text
[original stem]（活动图完善版）.docx
```

If the source file is read-only, copying may preserve read-only attributes. Clear them before saving:

```python
out_docx.chmod(0o666)
```

### 5. Replace Only The Target Section

Remove paragraphs between the target heading and the next heading, then insert the new content after the target heading.

Important:

- Insert in reverse order when repeatedly inserting immediately after the same anchor.
- Keep captions centered.
- Use Chinese fonts for Chinese report text, typically `宋体` for body/captions.
- Avoid adding unrelated document-wide formatting changes.

### 6. Verify Cheaply First

Before any heavy render:

- Confirm `3.2` still appears before `3.3`.
- Confirm the expected paragraph order.
- Confirm the expected number of images in the section.
- Open representative PNGs visually.
- Check image dimensions.

Example:

```python
from docx import Document
doc = Document("output.docx")
for i, p in enumerate(doc.paragraphs):
    if p.text.strip() == "3.2 活动图":
        for j in range(i, i + 25):
            print(j, repr(doc.paragraphs[j].text[:80]),
                  len(doc.paragraphs[j]._element.xpath(".//pic:pic")))
        break
```

### 7. Render Only At The End

Render checks are useful but can be slow or unavailable.

Try render only after structural checks pass:

- Use the documents plugin `render_docx.py` when LibreOffice is available.
- On Windows, `soffice.exe` may not be installed or may not be on PATH.
- Word COM automation can fail with `CO_E_SERVER_EXEC_FAILURE`.

If rendering fails because tooling is unavailable:

- Do not keep retrying blindly.
- State the limitation clearly.
- Rely on structure checks and direct PNG inspection.

## Common Pitfalls And Fixes

### Pitfall: Editing The TOC Entry

Symptom: changes appear near the beginning around lines like `3.2 活动图\t4`.

Fix: locate the later body heading. If there are multiple matches, use the last `3.2 活动图` before `3.3 状态图`.

### Pitfall: One Huge Activity Diagram

Symptom: leader/teacher says "为什么只有一个?" or the diagram is unreadable.

Fix: split by use-case groups and add split rationale.

### Pitfall: No Text Description

Symptom: diagram is inserted but report section feels empty.

Fix: add:

- One paragraph explaining what activity diagrams model.
- One paragraph explaining split logic.
- One paragraph before each diagram explaining that diagram's workflow and exceptions.

### Pitfall: Lines Cross Text

Symptom: arrows overlap node labels after scaling.

Fix:

- Remove nonessential exception loops.
- Put exception handling in a note box.
- Split the diagram.
- Use fewer decision nodes.

### Pitfall: Image Clipped In Word

Symptom: final node or note box is cut off.

Fix:

- Add bottom margin in the PNG.
- Increase canvas height rather than shrinking fonts.
- Keep final nodes away from the bottom border.

### Pitfall: Rebuilding The Whole Document

Symptom: long runtime and accidental changes elsewhere.

Fix: only replace paragraphs between the target heading and next heading; do not rewrite the whole doc.

## Suggested Text Templates

### General Activity Diagram Description

```text
活动图用于描述系统业务活动的执行顺序、条件分支以及不同参与对象之间的职责划分。KnoBrain系统包含普通用户学习流程和管理员后台维护流程，若只绘制一张总活动图，会导致节点过多、分支复杂，难以体现每个核心用例的处理逻辑。因此，本节按照用例关联关系将活动图拆分为四类：用户注册/登录、知识问答与关联推荐、学习日记与知识图谱及复习提醒、管理员后台管理。
```

### Split Rationale

```text
拆分后的活动图既能保持与用例描述的一致性，也能清晰展示普通用户、系统、数据库/外部服务、管理员之间的协作关系。其中前三张图描述普通用户从获取权限到完成学习闭环的主要活动，第四张图描述管理员保障系统稳定运行的后台活动。
```

## Output Checklist

Before final response:

- A new DOCX copy exists.
- The original DOCX is not overwritten unless requested.
- The target section contains prose, captions, and multiple diagrams.
- Captions are sequential and match the section number.
- Images are inspectable as standalone PNGs.
- Structural docx check passed.
- Render attempt status is known and reported honestly if unavailable.

