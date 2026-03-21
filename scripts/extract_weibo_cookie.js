/**
 * 微博 Cookie 提取脚本
 * 
 * 使用方法：
 * 1. 在浏览器中登录微博
 * 2. 登录成功后，按 F12 打开开发者工具
 * 3. 切换到 Console（控制台）标签
 * 4. 将本脚本内容复制并粘贴到控制台中
 * 5. 按回车键执行，Cookie 会自动复制到剪贴板
 * 
 * 注意事项：
 * - 请确保已在微博网站登录成功
 * - 脚本会自动提取 SUB 和 SUBP 两个关键 Cookie
 * - 提取成功后会自动复制到剪贴板
 * - 如果复制失败，会在控制台显示 Cookie 内容，可手动复制
 */

(function() {
  'use strict';

  console.log('🍪 开始提取微博 Cookie...');

  // 获取当前页面的所有 Cookie
  const cookies = document.cookie;
  
  if (!cookies || cookies.trim() === '') {
    console.error('❌ 未找到任何 Cookie，请确保已在微博网站登录');
    alert('❌ 未找到任何 Cookie，请确保已在微博网站登录');
    return;
  }

  // 将 Cookie 字符串解析为对象
  const cookieObj = {};
  cookies.split('; ').forEach(cookie => {
    const [name, value] = cookie.split('=');
    if (name && value) {
      cookieObj[name] = value;
    }
  });

  console.log('📋 检测到的 Cookie:', Object.keys(cookieObj));

  // 提取关键的 Cookie
  const importantCookies = ['SUB', 'SUBP'];
  const cookieParts = [];
  const missingCookies = [];

  importantCookies.forEach(name => {
    if (cookieObj[name]) {
      cookieParts.push(`${name}=${cookieObj[name]}`);
      console.log(`✓ 找到 ${name}: ${cookieObj[name].substring(0, 20)}...`);
    } else {
      missingCookies.push(name);
      console.warn(`✗ 未找到 ${name}`);
    }
  });

  // 检查是否找到所有必要的 Cookie
  if (cookieParts.length === 0) {
    console.error('❌ 未找到任何必要的 Cookie (SUB, SUBP)');
    console.error('当前页面 URL:', window.location.href);
    alert('❌ 未找到必要的 Cookie (SUB, SUBP)\\n\\n请确保：\\n1. 已在微博网站登录成功\\n2. 当前页面是 weibo.com 域名');
    return;
  }

  if (missingCookies.length > 0) {
    console.warn(`⚠️  警告：未找到以下 Cookie: ${missingCookies.join(', ')}`);
    console.warn('部分功能可能无法正常使用');
  }

  // 构建最终的 Cookie 字符串
  const cookieString = cookieParts.join('; ');
  console.log('✅ Cookie 提取成功！');
  console.log('Cookie 内容:', cookieString);

  // 尝试复制到剪贴板
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(cookieString)
      .then(() => {
        console.log('✅ Cookie 已复制到剪贴板！');
        alert(`✅ Cookie 已复制到剪贴板！\\n\\n${cookieString.substring(0, 50)}...\\n\\n请回到本页面粘贴到输入框中。`);
      })
      .catch(err => {
        console.error('❌ 自动复制失败:', err);
        console.log('📋 请手动复制以下内容:');
        console.log(cookieString);
        alert(`❌ 自动复制失败\\n\\n请查看控制台手动复制以下内容:\\n\\n${cookieString}`);
      });
  } else {
    // 浏览器不支持 Clipboard API
    console.log('📋 浏览器不支持自动复制，请手动复制以下内容:');
    console.log(cookieString);
    alert(`请手动复制以下内容:\\n\\n${cookieString}`);
  }
})();
