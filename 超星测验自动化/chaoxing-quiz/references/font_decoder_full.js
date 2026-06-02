/**
 * font-cxsecret 字体解密完整实现
 * 
 * 基于 Typr.js（从 OCS 网课助手脚本中提取）进行 TTF 字体解析，
 * 配合 OCS CDN 字体映射表 (table.json) 解密超星学习通的自定义字体混淆。
 * 
 * 依赖:
 * - references/typr_core.js (Typr.js 字体解析器，已包含在 skill 中)
 * - blueimp-md5 CDN (https://cdn.jsdelivr.net/npm/blueimp-md5@2.19.0/js/md5.min.js)
 * - OCS 字体映射表 (https://cdn.ocsjs.com/resources/font/table.json)
 * 
 * 用法 (在 playwright-cli 中):
 *   playwright-cli run-code --filename=.agents/skills/chaoxing-quiz/references/font_decoder_full.js
 * 
 * 原理:
 *   超星的 font-cxsecret 自定义字体中，中文字符的 glyph 被重新映射。
 *   DOM 中的 Unicode 字符（如 "机" → U+673A）实际显示的却是另一个字符（如 "彍"）。
 *   解码过程:
 *   1. 从 CSS @font-face 中提取 base64 编码的 TTF 字体
 *   2. 用 Typr.js 解析字体，获取每个字符 (U+4E00–U+9FFF) 的 glyph 路径
 *   3. 对 glyph 路径做 JSON.stringify 后计算 MD5，取后 8 位作为索引
 *   4. 从 OCS 预计算映射表 table.json 中查找对应的正确字符 Unicode
 *   5. 替换 .font-cxsecret 元素中的乱码为正确文字
 * 
 * 参考: OCS 网课助手 (https://github.com/ocsjs/ocsjs)
 */

async page => {
  let frame = page.frame({ url: /doHomeWorkNew/ });
  if (!frame) {
    await page.waitForTimeout(5000);
    frame = page.frames().find(f => f.url().includes('doHomeWorkNew'));
    if (!frame) return 'No homework frame found — navigate to quiz first';
  }

  // 1. 注入 Typr.js（本地文件）
  // playwright-cli 的 path 解析相对于当前工作目录；使用本机 skill 的绝对路径更稳。
  await frame.addScriptTag({ path: 'D:/PyCharm/CODE/Browser/.agents/skills/chaoxing-quiz/references/typr_core.js' });
  
  // 2. 注入 blueimp-md5
  await frame.addScriptTag({ url: 'https://cdn.jsdelivr.net/npm/blueimp-md5@2.19.0/js/md5.min.js' });
  await page.waitForTimeout(2000);

  // 3. 执行解码
  const result = await frame.evaluate(async () => {
    try {
      // 验证依赖就绪
      if (typeof Typr === 'undefined') return 'ERROR: Typr.js not loaded';
      if (typeof md5 === 'undefined') return 'ERROR: md5 not loaded';

      // 获取 CSS @font-face 中的 base64 字体
      const styleEl = Array.from(document.querySelectorAll('style')).find(
        s => s.textContent?.includes('font-cxsecret')
      );
      if (!styleEl) return 'NOTICE: no font-cxsecret found on this page';
      
      const match = styleEl.textContent.match(/base64,([\w\W]+?)'/);
      if (!match) return 'ERROR: no base64 font data found';

      // 解码 base64 → bytes
      const raw = atob(match[1]);
      const buf = new Uint8Array(raw.length);
      for (let i = 0; i < raw.length; i++) buf[i] = raw.charCodeAt(i);

      // 用 Typr.js 解析 TTF 字体
      const code = Typr.parse(buf);

      // 加载 OCS 预计算字体映射表
      const map = await fetch('https://cdn.ocsjs.com/resources/font/table.json').then(r => r.json());

      // 遍历 CJK 基本平面（U+4E00–U+9FFF），计算每个字符的 glyph 哈希并查映射
      const charMap = {};
      let hits = 0;
      for (let i = 0x4E00; i <= 0x9FFF; i++) {
        try {
          const glyph = Typr.U.codeToGlyph(code, i);
          if (!glyph) continue;
          const path = Typr.U.glyphToPath(code, glyph);
          const hex = md5(JSON.stringify(path)).slice(24); // OCS 取后 8 位
          if (map[hex]) { charMap[i] = map[hex]; hits++; }
        } catch (_) { /* skip glyphs that fail */ }
      }

      if (hits === 0) return 'WARN: no font mappings matched — font may be different';

      // 替换页面中所有 .font-cxsecret 元素的文字
      const elements = document.querySelectorAll('.font-cxsecret');
      elements.forEach(el => {
        let html = el.innerHTML;
        for (const key in charMap) {
          const a = String.fromCharCode(+key);
          const b = String.fromCharCode(charMap[key]);
          if (a !== b) html = html.split(a).join(b);
        }
        el.innerHTML = html;
        el.classList.remove('font-cxsecret'); // 移除混淆标记
      });

      return `OK: decoded ${hits} characters, replaced in ${elements.length} elements`;
    } catch (e) {
      return `ERROR: ${e.message}`;
    }
  });

  return result;
}
