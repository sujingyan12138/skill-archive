/**
 * font-cxsecret 字体解密工具
 * 
 * 超星学习通使用自定义字体 (font-cxsecret) 来混淆页面文字。
 * 工作原理：
 * 1. CSS @font-face 定义一个自定义字体，字符映射被改变
 * 2. DOM 中的 Unicode 字符（如 "机"）在自定义字体中显示为另一个字符（如 "彍"）
 * 3. 导致 innerText 提取的文字为乱码
 * 
 * 解码原理（参考 OCS 网课助手）：
 * 1. 从 CSS 中提取 base64 编码的 TTF 字体
 * 2. 解析字体的 glyph 路径
 * 3. 计算每个 glyph 的 MD5 哈希
 * 4. 通过 OCS CDN 的预计算映射表 (table.json) 查询原始字符
 * 
 * 注意: 此方法需要 typr.js 库解析字体文件。
 */

/**
 * 图片选项处理 — 通过 Playwright 截图绕过防盗链
 * 
 * 问题: 超星题库中的图片选项托管在 p.cldisk.com，
 * 直接 HTTP GET 会返回 403 (Referer + Cookie 防盗链)。
 * 
 * 解法: 在已登录的浏览器会话中，使用 Playwright 的 
 * element.screenshot() 截取图片元素的渲染内容。
 * 截图后可传给多模态模型 (GPT-4V/Claude) 直接读文字，
 * 或使用 OCR 引擎识别。
 * 
 * 用法 (在 playwright-cli run-code 中):
 *   const frame = page.frame({ url: /doHomeWorkNew/ });
 *   const imgEl = await frame.evaluateHandle(() => 
 *     document.querySelectorAll('.Zy_ulTop li .after img')[0]
 *   );
 *   await imgEl.screenshot({ path: 'option_text.png' });
 */

/**
 * 从页面 CSS 中提取 font-cxsecret 的 base64 字体数据
 */
function extractFontFromCSS(doc) {
  const styleEl = Array.from(doc.querySelectorAll('style')).find(
    style => style.textContent?.includes('font-cxsecret')
  );
  if (!styleEl) return null;
  
  const match = styleEl.textContent.match(/base64,([\w\W]+?)'/);
  return match ? match[1] : null;
}

/**
 * 获取 font-cxsecret 元素列表
 */
function getSecretFontElements(doc) {
  return Array.from(doc.querySelectorAll('.font-cxsecret')).map(el => {
    // 选项文本通常在 .after 元素中
    const after = el.querySelector('.after');
    return after || el;
  });
}

/**
 * 尝试读取选项文本的后备方法
 * 即使字体加密也能提取部分可读文本
 */
function extractOptionsText(questionEl) {
  const options = [];
  questionEl.querySelectorAll('.Zy_ulTop li').forEach(li => {
    const letter = li.querySelector('[data]')?.getAttribute('data') || '';
    const anchorEl = li.querySelector('.after a, .after p');
    
    // 方法1: 检查是否有 img 标签 (图片选项 — 有防盗链，需截图)
    // 图片 URL 无法直接 fetch，需要用 Playwright element.screenshot() 截取
    // 示例: await imgElementHandle.screenshot({ path: 'option.png' });
    const imgEl = li.querySelector('.after img');
    if (imgEl) {
      const imgSrc = imgEl.getAttribute('src') || '';
      options.push({ 
        letter, 
        type: 'image', 
        src: imgSrc,
        note: 'image has hotlink protection; use element.screenshot() to capture'
      });
      return;
    }
    
    // 方法2: 检查 aria-label
    const ariaLabel = li.getAttribute('aria-label') || '';
    if (ariaLabel && ariaLabel !== `${letter} 选择`) {
      options.push({ letter, type: 'text', text: ariaLabel });
      return;
    }
    
    // 方法3: 直接读取 innerText (可能乱码但保留原始字符)
    const text = anchorEl?.innerText?.trim() || '';
    options.push({ letter, type: 'font-cxsecret', rawText: text.substring(0, 60) });
  });
  
  return options;
}

/**
 * 检查页面是否使用了 font-cxsecret 字体
 */
function hasSecretFont(doc) {
  return Array.from(doc.querySelectorAll('style')).some(
    style => style.textContent?.includes('font-cxsecret')
  );
}
