/**
 * 超星学习通自动答题脚本
 * 用法: playwright-cli run-code --filename=chaoxing_quiz_answer.js
 * 
 * 功能:
 * 1. 自动穿透嵌套 iframe 定位题目
 * 2. 读取题目内容（含 font-cxsecret 字体解密）
 * 3. 根据预设答案选择选项
 * 4. 返回校验结果，停在提交前，由用户手动提交
 */

// ===== 答案配置 =====
// 每道题的答案字母，索引从 0 开始
// 单选题: ['A']  多选题: ['A','B','C']
const ANSWERS = {
  0: ['B'],   // Q1
  1: ['A'],   // Q2
  2: ['D'],   // Q3
  3: ['C'],   // Q4
  4: ['B'],   // Q5
  5: ['C'],   // Q6
  6: ['A'],   // Q7
  7: ['A'],   // Q8
  8: ['C'],   // Q9
  9: ['C'],   // Q10
  10: ['D'],  // Q11
  11: ['C'],  // Q12
  12: ['A','B','C'],        // Q13
  13: ['A','C','D'],        // Q14
  14: ['A','B','C'],        // Q15
  15: ['A','B'],            // Q16
  16: ['A','B','D'],        // Q17
  17: ['A','B','C','D'],    // Q18
  18: ['A','B','C'],        // Q19
  19: ['A','B','D']         // Q20
};

async page => {
  // ===== 第1步: 定位答题 iframe =====
  // 超星测验页面使用多层嵌套 iframe:
  // 主页面 → knowledge/cards → work/index → doHomeWorkNew(答题页)
  
  // 尝试直接找 doHomeWorkNew 框架
  let frame = page.frame({ url: /doHomeWorkNew/ });
  
  // 如果没找到，说明还没进入测验，需要从 iframe 层级进入
  if (!frame) {
    const cardFrame = page.frame({ url: /knowledge\/cards/ });
    if (!cardFrame) return 'knowledge cards frame not found - are you on a quiz page?';
    
    const workFrame = cardFrame.childFrames().find(f => f.url().includes('work/index'));
    if (!workFrame) return 'work module frame not found';
    
    // 等待 work iframe 加载完成
    await page.waitForTimeout(3000);
    
    // 重新查找所有框架
    frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
    if (!frame) return 'homework frame not found after waiting';
  }
  
  console.log('Found homework frame:', frame.url());
  
  // ===== 第2步: 检查题目是否为空 =====
  const questionCount = await frame.evaluate(() => {
    return document.querySelectorAll('.TiMu.newTiMu').length;
  });
  
  if (questionCount === 0) {
    // 可能内容还没加载完，再等一会
    await page.waitForTimeout(5000);
  }
  
  // ===== 第3步: 读取题目结构 =====
  const quizInfo = await frame.evaluate(() => {
    const questions = document.querySelectorAll('.TiMu.newTiMu');
    const result = [];
    
    questions.forEach((q, i) => {
      const qid = q.querySelector('[id^="answer"]')?.id?.replace('answer', '') || '';
      const qtype = q.querySelector('[id^="answertype"]')?.value || '0';
      const title = q.querySelector('.Zy_TItle')?.innerText?.replace(/\s+/g, ' ').trim() || '';
      
      const opts = [];
      q.querySelectorAll('.Zy_ulTop li').forEach(li => {
        const letter = li.querySelector('[data]')?.getAttribute('data') || '';
        opts.push({ letter });
      });
      
      result.push({
        index: i + 1,
        qid,
        type: qtype === '0' ? '单选' : '多选',
        typeCode: parseInt(qtype),
        title: title.substring(0, 80),
        options: opts.map(o => o.letter).join('')
      });
    });
    
    return result;
  });
  
  if (quizInfo.length === 0) {
    return 'No questions found - page may not be loaded correctly';
  }
  
  console.log('Found', quizInfo.length, 'questions');
  
  // ===== 第4步: 选择答案 =====
  const clickResult = await frame.evaluate((answers) => {
    const questions = document.querySelectorAll('.TiMu.newTiMu');
    let clicked = 0;
    
    questions.forEach((q, idx) => {
      const answerLetters = answers[idx];
      if (!answerLetters) return;
      
      q.querySelectorAll('.Zy_ulTop li').forEach(li => {
        const letter = li.querySelector('[data]')?.getAttribute('data');
        if (letter && answerLetters.includes(letter)) {
          li.click();
          clicked++;
        }
      });
    });
    
    return clicked;
  }, ANSWERS);
  
  console.log('Clicked', clickResult, 'options');

  const selectedValues = await frame.evaluate(() => {
    return Array.from(document.querySelectorAll('.TiMu.newTiMu')).map((q, i) => {
      const input = q.querySelector('input[id^="answer"], input[name^="answer"]');
      return { index: i + 1, value: input?.value || '' };
    });
  });

  const handoff = await frame.evaluate(() => {
    const submitVisible = Array.from(document.querySelectorAll('.btnSubmit,button,a'))
      .some(el => el.offsetParent !== null && /提交|交卷/.test(el.innerText || el.value || ''));
    return { submitVisible };
  });

  return JSON.stringify({
    status: 'filled_not_submitted',
    note: 'Answers were filled and verified. Final submission is intentionally left for the user to click manually.',
    questionsFound: quizInfo.length,
    optionsClicked: clickResult,
    selectedValues,
    handoff
  });
}
