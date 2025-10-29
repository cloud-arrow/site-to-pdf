# HTTrack 网站转 PDF - 使用指南

## 🎯 项目概述

这个工具可以将 HTTrack 抓取的网站转换为单个 PDF 文件，特别适合将在线文档、教程、博客等转换为离线阅读的 PDF 格式。

## ✨ 核心特性

- **智能页面排序**: 自动从侧边栏提取正确的页面顺序
- **高质量渲染**: 使用 Playwright + Chromium 保证与浏览器一致的渲染效果
- **自动目录生成**: 为 PDF 创建带层级结构的目录页
- **打印优化**: 自动隐藏侧边栏、导航栏，模拟浏览器打印效果
- **内容完整**: 强制表格和代码块换行，确保内容不被截断
- **过滤无关页面**: 自动排除 404 页面、缓存文件等
- **完整样式保留**: CSS、图片、代码高亮等完全保留

## 📦 安装依赖

### 方式一：使用安装脚本（推荐）

```bash
chmod +x install_dependencies.sh
./install_dependencies.sh
```

### 方式二：手动安装

```bash
# 安装 Python 依赖
pip3 install playwright beautifulsoup4 PyPDF2 lxml

# 安装 Playwright 浏览器
playwright install chromium

# 安装 HTTrack
sudo apt-get install httrack  # Ubuntu/Debian
sudo yum install httrack       # CentOS/RHEL
brew install httrack           # macOS
```

## 🚀 使用流程

### 步骤 1: 使用 HTTrack 抓取网站

```bash
# 基本用法
httrack https://example.com -O ./output

# 推荐用法（控制深度和连接数）
httrack https://www.laravelactions.com \
  -O ./laravelactions_site \ 
  -%v \                       
  -c4 \                      
  -r3 \                       
  +*.laravelactions.com/* \   
  -s0                         
```

**重要参数说明：**
- `-r3`: 递归深度 3 层，太深会抓取过多页面，太浅会遗漏内容
- `-c4`: 4 个并发连接，平衡速度和服务器负载
- `+*.domain.com/*`: 限制只抓取指定域名，避免跟随外部链接
- `-s0`: 不抓取外部样式表的外部资源

### 步骤 2: 转换为 PDF

```bash
# 基本用法
python3 site_to_pdf.py ./output/www.example.com -o website.pdf

# 使用所有选项
python3 site_to_pdf.py \
  ./laravelactions_site/www.laravelactions.com \
  -o laravelactions.pdf \        # 输出文件名
  -b chromium \                  # 浏览器类型
  --max-pages 100 \              # 限制最多转换 100 页
  --no-toc \                     # 不生成目录页
  --keep-sidebar                 # 保留侧边栏（默认隐藏）
```

## 🎛️ 命令行选项

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `httrack_dir` | HTTrack 输出目录（必需） | - |
| `-o, --output` | 输出 PDF 文件名 | `website.pdf` |
| `-b, --browser` | 浏览器类型 (chromium/firefox/webkit) | `chromium` |
| `--max-pages` | 最大转换页面数 | 无限制 |
| `--no-toc` | 不生成目录页 | 生成目录 |
| `--keep-sidebar` | 保留侧边栏和导航栏 | 隐藏侧边栏 |

## 📊 实际测试结果

### 测试案例 1: Laravel Actions 文档

```bash
# 1. 抓取网站
httrack https://www.laravelactions.com \
  -O ./laravelactions_site \
  -r3 -c10 -s0 \
  +*.laravelactions.com/*

# 抓取结果:
# - HTML 页面: 43 个（过滤掉 404 页面后）
# - 数据量: ~4 MB

# 2. 转换为 PDF
python3 site_to_pdf.py \
  ./laravelactions_site/www.laravelactions.com \
  -o laravelactions.pdf

# 转换结果:
# - 页数: 127 页
# - 文件大小: ~7 MB
# - 包含: 层级目录 + 43 个文档页面
```

### 测试案例 2: Browsertrix Crawler 文档

```bash
# 1. 抓取网站
httrack https://crawler.docs.browsertrix.com/ \
  -O browsertrix_site \
  -r3 -c10 -s0 \
  +crawler.docs.browsertrix.com/*

# 抓取结果:
# - 用时: 14 秒
# - 文件数: 24 个
# - HTML 页面: 15 个

# 2. 转换为 PDF
python3 site_to_pdf.py \
  ./browsertrix_site/crawler.docs.browsertrix.com \
  -o browsertrix.pdf

# 转换结果:
# - 页数: 约 40 页
# - 文件大小: 3.7 MB
# - 包含: 层级目录 + 15 个文档页面
```

## 🎨 转换后的 PDF 特点

✅ **层级化的目录结构**
- 自动生成带层级缩进的目录页
- 按照原网站的侧边栏顺序排列
- 不同深度用不同颜色标识
- 保留完整的相对路径信息

✅ **打印优化布局**
- 自动隐藏侧边栏和导航栏（可选保留）
- 模拟浏览器打印效果
- 强制表格和代码块内容换行
- 确保所有内容完整显示，无截断

✅ **高质量渲染**
- 完整的 CSS 样式
- 代码高亮语法着色
- 保留所有图片和图标
- 正确的字体和排版

✅ **智能过滤**
- 自动排除 404 错误页面
- 过滤缓存和日志文件
- 去除临时文件

## ⚙️ 高级配置

### 自定义浏览器

```bash
# 使用 Firefox
python3 site_to_pdf.py ./output -o site.pdf -b firefox

# 使用 WebKit
python3 site_to_pdf.py ./output -o site.pdf -b webkit
```

### 限制页面数量

适用于大型网站，只转换前 N 个页面：

```bash
python3 site_to_pdf.py ./output -o site.pdf --max-pages 50
```

### 不生成目录

如果不需要目录页：

```bash
python3 site_to_pdf.py ./output -o site.pdf --no-toc
```

### 保留侧边栏

如果想保留网站原有的侧边栏和导航栏：

```bash
python3 site_to_pdf.py ./output -o site.pdf --keep-sidebar
```

## 🔧 故障排除

### 问题 1: HTTrack 抓取失败或文件为空

**症状**: 生成的 HTML 文件为 0 字节

**解决方案**:
- 减少递归深度 (`-r2` 或 `-r3`)
- 减少并发连接 (`-c2` 或 `-c4`)
- 检查网络连接
- 某些网站可能有反爬虫机制，尝试添加延迟

### 问题 2: PDF 文件太大

**解决方案**:
```bash
# 使用 --max-pages 限制页面数
python3 site_to_pdf.py ./output -o site.pdf --max-pages 30

# HTTrack 抓取时使用 -s0 不抓取外部资源
httrack https://example.com -O ./output -s0
```

### 问题 3: 表格或代码内容被截断

**症状**: PDF 中的表格或代码块右侧被截断

**原因**: 
- 网站本身打印样式不完善
- 内容过宽超出 A4 纸张范围

**当前方案**:
脚本已经注入强制换行的 CSS，确保内容完整显示。虽然表格列宽可能不够美观，但内容是完整的。

**注意**: 这是打印到固定纸张大小的固有限制。如需更美观的布局，建议：
- 直接在浏览器中打印原网站查看效果
- 或使用更宽的纸张尺寸（需修改脚本中的 `@page` 设置）

### 问题 4: 页面顺序不正确

**解决方案**:
脚本会自动从首页的侧边栏提取正确顺序。如果顺序仍不对：
- 确保 HTTrack 完整抓取了首页 (`index.html`)
- 检查首页是否包含侧边栏导航
- 手动检查 `page_info` 中的链接关系

### 问题 5: 某些页面内容缺失

**解决方案**:
如果是动态内容：
- 增加等待时间（脚本中 `asyncio.sleep(1.5)` 可以调大）
- 确保 HTTrack 抓取了所有必需的 JavaScript 文件

## 📝 目录结构

```
sitetopdf/
├── site_to_pdf.py              # 主脚本
├── install_dependencies.sh     # 依赖安装脚本
├── README.md                   # 项目说明
├── USAGE.md                    # 本文件：详细使用指南
├── CHANGELOG.md                # 更新日志
├── TEST_RESULTS.md             # 测试结果
├── httrack.md                  # HTTrack 使用说明
├── browsertrix_site/           # 示例：HTTrack 抓取结果
│   └── crawler.docs.browsertrix.com/
│       ├── index.html
│       ├── user-guide/
│       └── ...
└── browsertrix_fixed.pdf       # 示例：生成的 PDF
```

## 💡 最佳实践

### 1. 选择合适的递归深度

- **文档网站**: `-r2` 或 `-r3` 通常足够
- **博客网站**: `-r3` 或 `-r4`
- **大型网站**: 谨慎使用 `-r5` 以上

### 2. 使用域名限制

始终添加域名过滤，避免跟随外部链接：
```bash
httrack https://example.com +*.example.com/*
```

### 3. 控制并发数

- **小型服务器**: `-c2` 或 `-c4`
- **大型网站**: `-c8` 或 `-c10`
- **本地测试**: `-c1`

### 4. 预览结果

转换大型网站前，先用 `--max-pages 10` 测试：
```bash
python3 site_to_pdf.py ./output -o test.pdf --max-pages 10
```

### 5. 内容完整性 vs 美观度

脚本优先保证**内容完整**，表格可能出现列宽不均匀的情况。这是将网页内容适配固定纸张大小的必然取舍：
- ✅ 内容完整，不会被截断
- ⚠️ 表格布局可能不如原网站美观
- 💡 如需更美观的效果，建议直接使用浏览器的原生打印功能

## 🎓 示例用途

- 📚 **技术文档离线化**: Laravel、Vue.js、React 等框架文档
- 📖 **在线教程保存**: 编程教程、课程材料
- 🗂️ **知识归档**: 博客文章、技术博客合集
- 📄 **项目文档**: 项目 Wiki、内部文档

## 🔗 相关链接

- [HTTrack 官网](https://www.httrack.com/)
- [Playwright 文档](https://playwright.dev/python/)
- [BeautifulSoup 文档](https://www.crummy.com/software/BeautifulSoup/)

## 📧 反馈与贡献

如有问题或建议，欢迎提交 Issue 或 Pull Request！

---

**最后更新**: 2025-10-29
