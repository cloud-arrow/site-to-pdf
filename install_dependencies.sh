#!/bin/bash
# 安装 HTTrack 网站转 PDF 工具的依赖

set -e

echo "========================================="
echo "安装 HTTrack 网站转 PDF 工具依赖"
echo "========================================="
echo ""

# 检查 Python 版本
echo "检查 Python 版本..."
python3 --version || { echo "错误: 未安装 Python3"; exit 1; }
echo ""

# 安装 Python 依赖
echo "安装 Python 依赖包..."
pip3 install --upgrade pip
pip3 install playwright beautifulsoup4 PyPDF2 lxml
echo "✓ Python 依赖安装完成"
echo ""

# 安装 Playwright 浏览器
echo "安装 Playwright 浏览器..."
playwright install chromium
echo "✓ Playwright 浏览器安装完成"
echo ""

# 安装 HTTrack
echo "安装 HTTrack..."
if command -v apt-get &> /dev/null; then
    echo "检测到 Debian/Ubuntu 系统"
    sudo apt-get update
    sudo apt-get install -y httrack
elif command -v yum &> /dev/null; then
    echo "检测到 CentOS/RHEL 系统"
    sudo yum install -y httrack
elif command -v pacman &> /dev/null; then
    echo "检测到 Arch Linux 系统"
    sudo pacman -S --noconfirm httrack
elif command -v brew &> /dev/null; then
    echo "检测到 macOS 系统"
    brew install httrack
else
    echo "警告: 无法自动安装 HTTrack，请手动安装"
fi
echo "✓ HTTrack 安装完成"
echo ""

echo "========================================="
echo "所有依赖安装完成！"
echo "========================================="
echo ""
echo "使用方法:"
echo "1. 使用 HTTrack 抓取网站:"
echo "   httrack https://example.com -O ./output"
echo ""
echo "2. 转换为 PDF:"
echo "   python3 site_to_pdf.py ./output -o website.pdf"
echo ""
