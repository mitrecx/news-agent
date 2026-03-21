#!/bin/bash
# ChromeDriver 安装脚本
# 用于在 Linux 服务器上安装 ChromeDriver

set -e

echo "======================================"
echo "  ChromeDriver 安装脚本"
echo "======================================"

# 检查 Chrome 版本
CHROME_VERSION=$(google-chrome --version | awk '{print $3}')
echo "检测到 Chrome 版本: $CHROME_VERSION"

# 提取主版本号
MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d. -f1)
echo "主版本号: $MAJOR_VERSION"

# 创建临时目录
TMP_DIR=$(mktemp -d)
echo "临时目录: $TMP_DIR"

cd $TMP_DIR

# 尝试从多个源下载 ChromeDriver
echo ""
echo "尝试下载 ChromeDriver..."

SUCCESS=false

# 方法1: 使用清华镜像
echo "方法1: 尝试清华镜像..."
for url in \
    "https://mirrors.tuna.tsinghua.edu.cn/chromedriver-for-testing/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" \
    "https://mirrors.tuna.tsinghua.edu.cn/chromedriver-for-testing/LATEST_RELEASE_${MAJOR_VERSION}/chromedriver-linux64.zip"
do
    echo "  尝试: $url"
    if wget --timeout=30 -q "$url" -O chromedriver.zip 2>/dev/null && [ -s chromedriver.zip ]; then
        echo "  ✓ 下载成功"
        SUCCESS=true
        break
    fi
done

# 方法2: 使用阿里云镜像
if [ "$SUCCESS" = false ]; then
    echo "方法2: 尝试阿里云镜像..."
    for url in \
        "https://cdn.npmmirror.com/binaries/chromedriver-for-testing/${CHROME_VERSION}/linux64/chromedriver-linux64.zip" \
        "https://registry.npmmirror.com/-/binary/chromedriver-for-testing/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"
    do
        echo "  尝试: $url"
        if wget --timeout=30 -q "$url" -O chromedriver.zip 2>/dev/null && [ -s chromedriver.zip ]; then
            echo "  ✓ 下载成功"
            SUCCESS=true
            break
        fi
    done
fi

# 方法3: 使用官方源（可能需要代理）
if [ "$SUCCESS" = false ]; then
    echo "方法3: 尝试官方源..."
    url="https://storage.googleapis.com/chrome-for-testing-public/${CHROME_VERSION}/linux64/chromedriver-linux64.zip"
    echo "  尝试: $url"
    if wget --timeout=30 "$url" -O chromedriver.zip 2>/dev/null && [ -s chromedriver.zip ]; then
        echo "  ✓ 下载成功"
        SUCCESS=true
    fi
fi

if [ "$SUCCESS" = false ]; then
    echo ""
    echo "❌ 所有下载源均失败"
    echo ""
    echo "请尝试手动安装："
    echo "1. 访问 https://googlechromelabs.github.io/chrome-for-testing/"
    echo "2. 下载对应版本的 ChromeDriver"
    echo "3. 上传到服务器并解压"
    echo "4. 复制到 /usr/local/bin/chromedriver"
    echo "5. 添加执行权限: chmod +x /usr/local/bin/chromedriver"
    echo ""
    cd /
    rm -rf $TMP_DIR
    exit 1
fi

# 解压文件
echo ""
echo "解压 ChromeDriver..."
unzip -q chromedriver.zip

# 查找 chromedriver 文件
CHROMEDRIVER=$(find . -name "chromedriver" -type f | head -1)

if [ -z "$CHROMEDRIVER" ]; then
    echo "❌ 未找到 chromedriver 文件"
    cd /
    rm -rf $TMP_DIR
    exit 1
fi

# 安装 ChromeDriver
echo "安装 ChromeDriver 到 /usr/local/bin/..."
sudo cp $CHROMEDRIVER /usr/local/bin/chromedriver
sudo chmod +x /usr/local/bin/chromedriver

# 清理临时文件
cd /
rm -rf $TMP_DIR

# 验证安装
echo ""
echo "验证安装..."
if /usr/local/bin/chromedriver --version &>/dev/null; then
    VERSION=$(/usr/local/bin/chromedriver --version 2>&1 | head -1)
    echo "✅ ChromeDriver 安装成功！"
    echo "版本: $VERSION"
    echo "路径: /usr/local/bin/chromedriver"
else
    echo "❌ ChromeDriver 安装失败"
    exit 1
fi

echo ""
echo "======================================"
echo "  安装完成！"
echo "======================================"
