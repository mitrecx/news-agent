"""
快速提取微博 Cookie 的辅助工具

使用方法：
1. 确保已在浏览器中登录微博
2. 打开浏览器开发者工具（F12）
3. 在 Console（控制台）中复制并运行下面的 JavaScript 代码
4. 将输出的 Cookie 复制粘贴到 .env 文件
"""

# JavaScript 代码（在浏览器 Console 中运行）
JS_CODE = """
// 提取微博 Cookie
(function() {
    const cookies = document.cookie.split(';').map(c => c.trim());
    const needed = ['SUB', 'SUBP', 'ALF'];
    const found = [];

    needed.forEach(name => {
        const cookie = cookies.find(c => c.startsWith(name + '='));
        if (cookie) {
            found.push(cookie);
        }
    });

    if (found.length === 3) {
        console.log('✅ 找到所有需要的 Cookie！');
        console.log('\\n请复制下面这一行到 .env 文件：');
        console.log('WEIBO_COOKIE=' + found.join('; '));
    } else {
        console.log('❌ 未找到完整的 Cookie');
        console.log('找到的 Cookie:', found);
        console.log('\\n请确保：');
        console.log('1. 已登录微博');
        console.log('2. 当前在 weibo.com 或 s.weibo.com 页面');
    }
})();
"""

if __name__ == "__main__":
    print("=" * 60)
    print("微博 Cookie 快速提取工具")
    print("=" * 60)
    print()
    print("请按以下步骤操作：")
    print()
    print("1. 打开浏览器，访问 https://weibo.com")
    print("2. 确保已登录")
    print("3. 按 F12 打开开发者工具")
    print("4. 点击 'Console'（控制台）标签")
    print("5. 复制下面的代码并粘贴到控制台，按回车：")
    print()
    print("-" * 60)
    print(JS_CODE)
    print("-" * 60)
    print()
    print("6. 控制台会输出类似这样的内容：")
    print("   WEIBO_COOKIE=SUB=xxx; SUBP=yyy; ALF=zzz")
    print()
    print("7. 将输出的内容复制到 .env 文件中")
    print()
    print("=" * 60)
