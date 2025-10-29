#!/usr/bin/env python3
"""
HTTrack 网站转 PDF 工具 (使用 Playwright)
将 HTTrack 抓取的网站转换为单个 PDF 文件
"""

import sys
import argparse
import asyncio
import tempfile
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from PyPDF2 import PdfMerger
from playwright.async_api import async_playwright
from typing import List, Dict, Set
from urllib.parse import unquote

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SiteToPDF:
    def __init__(self, 
                 httrack_dir: str, 
                 output_pdf: str = "website.pdf",
                 browser_type: str = "chromium",
                 max_pages: int = None,
                 include_toc: bool = True,
                 hide_sidebar: bool = True):
        """
        初始化转换器
        
        Args:
            httrack_dir: HTTrack 输出目录
            output_pdf: 输出 PDF 文件名
            browser_type: 浏览器类型 (chromium/firefox/webkit)
            max_pages: 最大转换页面数
            include_toc: 是否包含目录
            hide_sidebar: 是否隐藏侧边栏和导航栏
        """
        self.httrack_dir = Path(httrack_dir).resolve()
        self.output_pdf = output_pdf
        self.browser_type = browser_type
        self.max_pages = max_pages
        self.include_toc = include_toc
        self.hide_sidebar = hide_sidebar
        
        self.html_files: List[Path] = []
        self.page_info: Dict[str, Dict] = {}
        self.visited_pages: Set[str] = set()
        
    def find_html_files(self) -> List[Path]:
        """递归查找所有 HTML 文件"""
        logger.info("正在搜索 HTML 文件...")
        
        html_patterns = ['*.html', '*.htm']
        html_files = []
        
        for pattern in html_patterns:
            html_files.extend(self.httrack_dir.rglob(pattern))
        
        # 过滤排除项
        exclude_patterns = [
            'hts-cache', 'hts-log', 
            'backblue.gif', 'fade.gif',
            'index.html~',  # 临时文件
            '/404',  # 404 错误页面
        ]
        
        self.html_files = [
            f for f in html_files 
            if not any(pattern in str(f) for pattern in exclude_patterns)
        ]
        
        logger.info(f"找到 {len(self.html_files)} 个 HTML 文件")
        return self.html_files
    
    def analyze_page_structure(self):
        """分析页面结构和链接关系"""
        logger.info("分析页面链接关系...")
        
        for html_file in self.html_files:
            try:
                with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    soup = BeautifulSoup(content, 'html.parser')
                
                # 提取页面信息
                title = soup.find('title')
                title_text = title.get_text().strip() if title else html_file.stem
                
                # 提取元数据
                meta_description = soup.find('meta', attrs={'name': 'description'})
                description = meta_description.get('content', '') if meta_description else ''
                
                # 提取所有内部链接
                links = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    # 清理链接
                    href = unquote(href.split('#')[0].split('?')[0])
                    
                    if href and (href.endswith(('.html', '.htm')) or href.endswith('/')):
                        links.append(href)
                
                # 提取页面层级（基于路径深度）
                relative_path = html_file.relative_to(self.httrack_dir)
                depth = len(relative_path.parts) - 1
                
                self.page_info[str(html_file)] = {
                    'title': title_text,
                    'description': description,
                    'links': list(set(links)),  # 去重
                    'file': html_file,
                    'depth': depth,
                    'size': html_file.stat().st_size,
                    'relative_path': str(relative_path)
                }
                
            except Exception as e:
                logger.error(f"解析文件 {html_file} 时出错: {e}")
    
    def find_start_page(self) -> str:
        """查找网站首页"""
        # 优先级顺序
        index_names = [
            'index.html', 'index.htm', 
            'home.html', 'home.htm',
            'default.html', 'default.htm',
            'main.html', 'main.htm'
        ]
        
        # 在根目录查找
        for name in index_names:
            index_file = self.httrack_dir / name
            if index_file.exists():
                logger.info(f"找到首页: {name}")
                return str(index_file)
        
        # 查找最短路径的 index 文件
        index_files = [f for f in self.html_files if 'index' in f.name.lower()]
        if index_files:
            shortest = min(index_files, key=lambda x: len(str(x)))
            logger.info(f"使用首页: {shortest.name}")
            return str(shortest)
        
        # 返回深度最小的文件
        if self.html_files:
            sorted_files = sorted(
                self.html_files, 
                key=lambda x: len(x.relative_to(self.httrack_dir).parts)
            )
            logger.info(f"使用首页: {sorted_files[0].name}")
            return str(sorted_files[0])
        
        return None
    
    def build_page_tree(self) -> List[str]:
        """构建页面树结构（使用侧边栏顺序或广度优先遍历）"""
        start_page = self.find_start_page()
        if not start_page:
            return [str(f) for f in self.html_files]
        
        # 尝试从首页提取侧边栏链接顺序
        ordered_pages = self._extract_sidebar_order(start_page)
        
        if ordered_pages:
            logger.info(f"使用侧边栏顺序，找到 {len(ordered_pages)} 个页面")
            # 添加任何未在侧边栏中的页面
            for page_path in self.page_info.keys():
                if page_path not in ordered_pages:
                    ordered_pages.append(page_path)
        else:
            # 回退到广度优先遍历
            logger.info("使用广度优先遍历")
            ordered_pages = []
            queue = [start_page]
            self.visited_pages.clear()
            
            while queue and (not self.max_pages or len(ordered_pages) < self.max_pages):
                current_page = queue.pop(0)
                
                if current_page in self.visited_pages:
                    continue
                
                # 检查文件是否存在
                if not Path(current_page).exists():
                    current_page = self._resolve_page_path(current_page)
                    if not current_page:
                        continue
                
                self.visited_pages.add(current_page)
                ordered_pages.append(current_page)
                
                # 添加链接页面到队列
                if current_page in self.page_info:
                    for link in self.page_info[current_page]['links']:
                        linked_page = self._resolve_link(current_page, link)
                        if linked_page and linked_page not in self.visited_pages:
                            queue.append(linked_page)
            
            # 添加未访问的页面
            for page_path in self.page_info.keys():
                if page_path not in ordered_pages:
                    if not self.max_pages or len(ordered_pages) < self.max_pages:
                        ordered_pages.append(page_path)
        
        logger.info(f"页面树构建完成，共 {len(ordered_pages)} 个页面")
        return ordered_pages
    
    def _extract_sidebar_order(self, index_page: str) -> List[str]:
        """从首页侧边栏提取页面顺序"""
        try:
            with open(index_page, 'r', encoding='utf-8', errors='ignore') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            
            ordered_pages = [index_page]  # 首页放在第一位
            
            # 查找侧边栏链接
            sidebar = soup.find('aside', class_='sidebar')
            if not sidebar:
                sidebar = soup.find('ul', class_='sidebar-links')
            
            if sidebar:
                # 按顺序提取所有链接
                for link in sidebar.find_all('a', class_='sidebar-link'):
                    href = link.get('href', '')
                    if href and not href.startswith(('http://', 'https://', '#')):
                        # 解析相对路径
                        linked_page = self._resolve_link(index_page, href)
                        if linked_page and linked_page not in ordered_pages:
                            ordered_pages.append(linked_page)
                
                return ordered_pages
            
            return []
        except Exception as e:
            logger.warning(f"无法提取侧边栏顺序: {e}")
            return []
    
    def _resolve_link(self, current_page: str, link: str) -> str:
        """解析链接为绝对路径"""
        current_dir = Path(current_page).parent
        
        # 处理相对链接
        if not link.startswith(('http://', 'https://')):
            # 移除前导 ./
            link = link.lstrip('./')
            
            if link.startswith('/'):
                # 绝对路径（相对于网站根目录）
                linked_file = self.httrack_dir / link.lstrip('/')
            else:
                # 相对路径
                linked_file = current_dir / link
            
            # 处理目录链接
            if link.endswith('/'):
                linked_file = linked_file / 'index.html'
            
            # 规范化路径
            try:
                linked_file = linked_file.resolve()
                if linked_file.exists() and linked_file.is_file():
                    return str(linked_file)
            except Exception:
                pass
        
        return None
    
    def _resolve_page_path(self, page_path: str) -> str:
        """尝试解析页面路径"""
        # 尝试添加 index.html
        if page_path.endswith('/'):
            index_path = Path(page_path) / 'index.html'
            if index_path.exists():
                return str(index_path)
        
        return None
    
    async def html_to_pdf(self, page, html_file: str, pdf_file: str) -> bool:
        """使用 Playwright 将 HTML 转换为 PDF - 完全模拟浏览器打印"""
        try:
            # 提前设置更宽视口，减少布局换行导致的截断
            try:
                await page.set_viewport_size({"width": 2048, "height": 1400})
            except Exception:
                pass

            # 模拟打印介质（让浏览器采用 print 媒体规则）
            try:
                await page.emulate_media(media="print")
            except Exception:
                pass

            # 加载本地文件并等待网络空闲
            file_url = Path(html_file).as_uri()
            await page.goto(file_url, wait_until='networkidle', timeout=60000)

            # 等主要内容渲染
            try:
                await page.wait_for_selector('.theme-default-content, .content__default, main', timeout=10000)
            except Exception:
                pass

            # 兜底打印样式：终极推土机策略 - 强制所有内容可见和换行
            css_rules = [
                "@page { size: A4; margin: 10mm 10mm 12mm 10mm; }",
                # 全局覆盖 - 强制所有元素可见
                "* { overflow: visible !important; max-width: none !important; }",
                "html, body { width: auto !important; overflow: visible !important; }",
                "body, .theme-container, main, .page, .theme-default-content, div, section { max-width: none !important; width: auto !important; }",
                "img, svg, video, canvas { max-width: 100% !important; height: auto !important; }",
                ".theme-container { padding-left: 0 !important; padding-right: 0 !important; }",
                "main.page, .page, main { margin: 0 !important; padding: 0 8mm !important; }",
                ".theme-default-content, .content__default { width: 100% !important; padding: 0 !important; }",
                # 代码块强制换行
                "pre, pre code, code { white-space: pre-wrap !important; word-break: break-all !important; overflow-wrap: break-word !important; }",
                # 表格 - 保证内容完整但不过度拆分单词
                "table { table-layout: auto !important; width: 100% !important; border-collapse: collapse !important; overflow: visible !important; }",
                "table td, table th { white-space: normal !important; overflow-wrap: break-word !important; overflow: visible !important; padding: 6px !important; font-size: 12px !important; line-height: 1.5 !important; }",
                "table td code, table th code { white-space: pre-wrap !important; word-break: break-all !important; }",
                # 避免固定定位元素覆盖内容
                "[style*='position:fixed'], [style*='position: fixed'] { display: none !important; }",
                # 避免在关键元素内部分页
                "tr, pre, code, figure { page-break-inside: avoid !important; }",
            ]

            if self.hide_sidebar:
                css_rules.append(".sidebar, aside.sidebar, .sidebar-mask, .navbar, header.navbar, nav, .page-edit, .page-nav, .search-box, .sidebar-button, .global-ui { display: none !important; }")

            await page.add_style_tag(content="\n".join(css_rules))

            # 等样式应用
            await asyncio.sleep(0.5)

            # 导出为 A4，保留背景；更小的缩放以容纳更多内容
            await page.pdf(
                path=pdf_file,
                print_background=True,
                prefer_css_page_size=True, # 优先使用 @page
                scale=0.85
            )
            return True
        except Exception as e:
            logger.error(f"转换 {Path(html_file).name} 时出错: {e}")
            return False
    
    def generate_toc_html(self, page_order: List[str]) -> str:
        """生成目录页面（带层级结构）"""
        total_pages = len(page_order)
        toc_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>目录</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .toc-item {{
            margin: 8px 0;
            padding: 8px 10px;
            border-left: 3px solid #ddd;
            transition: all 0.2s;
        }}
        .toc-item:hover {{
            background-color: #f5f5f5;
            border-left-color: #4CAF50;
        }}
        .toc-item.depth-0 {{
            margin-left: 0;
            border-left-color: #4CAF50;
            background-color: #f9f9f9;
        }}
        .toc-item.depth-1 {{
            margin-left: 20px;
            border-left-color: #2196F3;
        }}
        .toc-item.depth-2 {{
            margin-left: 40px;
            border-left-color: #FF9800;
        }}
        .toc-item.depth-3 {{
            margin-left: 60px;
            border-left-color: #9C27B0;
        }}
        .toc-item.depth-4 {{
            margin-left: 80px;
        }}
        .page-number {{
            color: #666;
            font-weight: bold;
            margin-right: 10px;
            min-width: 30px;
            display: inline-block;
        }}
        .page-title {{
            color: #333;
            font-size: 15px;
            font-weight: 500;
        }}
        .page-path {{
            color: #999;
            font-size: 11px;
            margin-top: 4px;
            font-family: monospace;
        }}
        .depth-indicator {{
            color: #bbb;
            margin-right: 5px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>📚 网站目录</h1>
    <p>共 <strong>{total_pages}</strong> 个页面</p>
    <hr>
"""
        
        for i, page_path in enumerate(page_order, 1):
            info = self.page_info.get(page_path, {})
            title = info.get('title', Path(page_path).name)
            relative_path = info.get('relative_path', '')
            depth = info.get('depth', 0)
            
            # 限制最大深度显示
            display_depth = min(depth, 4)
            
            # 生成层级指示符
            indent_symbol = "└─ " if depth > 0 else ""
            
            toc_html += f"""    <div class="toc-item depth-{display_depth}">
        <span class="page-number">{i}.</span>
        <span class="depth-indicator">{indent_symbol}</span>
        <span class="page-title">{title}</span>
        <div class="page-path">{relative_path}</div>
    </div>
"""
        
        toc_html += """</body>
</html>
"""
        return toc_html
    
    async def convert(self):
        """执行完整的转换流程"""
        logger.info("开始转换网站为 PDF...")
        
        # 1. 查找 HTML 文件
        if not self.find_html_files():
            logger.error("未找到 HTML 文件")
            return False
        
        # 2. 分析页面结构
        self.analyze_page_structure()
        
        # 3. 构建页面树
        page_order = self.build_page_tree()
        
        if not page_order:
            logger.error("没有可转换的页面")
            return False
        
        logger.info(f"准备转换 {len(page_order)} 个页面")
        
        # 4. 使用 Playwright 转换
        async with async_playwright() as p:
            # 启动浏览器
            logger.info(f"启动 {self.browser_type} 浏览器...")
            
            if self.browser_type == "chromium":
                browser = await p.chromium.launch(headless=True)
            elif self.browser_type == "firefox":
                browser = await p.firefox.launch(headless=True)
            elif self.browser_type == "webkit":
                browser = await p.webkit.launch(headless=True)
            else:
                logger.error(f"不支持的浏览器类型: {self.browser_type}")
                return False
            
            page = await browser.new_page()
            
            # 5. 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                pdf_files = []
                
                # 生成目录页
                if self.include_toc:
                    logger.info("生成目录页...")
                    toc_html = self.generate_toc_html(page_order)
                    toc_file = Path(temp_dir) / "toc.html"
                    toc_file.write_text(toc_html, encoding='utf-8')
                    
                    toc_pdf = Path(temp_dir) / "000_toc.pdf"
                    if await self.html_to_pdf(page, str(toc_file), str(toc_pdf)):
                        pdf_files.append(str(toc_pdf))
                
                # 6. 逐个转换页面
                for i, page_path in enumerate(page_order, 1):
                    page_name = Path(page_path).name
                    logger.info(f"[{i}/{len(page_order)}] 转换: {page_name}")
                    
                    pdf_file = Path(temp_dir) / f"page_{i:04d}.pdf"
                    
                    if await self.html_to_pdf(page, page_path, str(pdf_file)):
                        pdf_files.append(str(pdf_file))
                    else:
                        logger.warning(f"跳过页面: {page_name}")
                
                await browser.close()
                
                # 7. 合并 PDF
                if pdf_files:
                    logger.info(f"合并 {len(pdf_files)} 个 PDF 文件...")
                    return self.merge_pdfs(pdf_files)
                else:
                    logger.error("没有成功转换的 PDF 文件")
                    return False
    
    def merge_pdfs(self, pdf_files: List[str]) -> bool:
        """合并多个 PDF 文件"""
        try:
            merger = PdfMerger()
            
            for pdf_file in pdf_files:
                if Path(pdf_file).exists():
                    merger.append(pdf_file)
            
            merger.write(self.output_pdf)
            merger.close()
            
            logger.info(f"✅ PDF 已保存至: {self.output_pdf}")
            
            # 显示文件大小
            size_mb = Path(self.output_pdf).stat().st_size / (1024 * 1024)
            logger.info(f"文件大小: {size_mb:.2f} MB")
            
            return True
            
        except Exception as e:
            logger.error(f"合并 PDF 时出错: {e}")
            return False


async def main():
    parser = argparse.ArgumentParser(
        description='将 HTTrack 抓取的网站转换为 PDF (Playwright 版本)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s /path/to/httrack/output
  %(prog)s /path/to/httrack/output -o website.pdf
  %(prog)s /path/to/httrack/output -o site.pdf -b firefox --max-pages 50
  %(prog)s /path/to/httrack/output --no-toc --keep-sidebar
        """
    )
    
    parser.add_argument('httrack_dir', help='HTTrack 输出目录路径')
    parser.add_argument('-o', '--output', default='website.pdf', 
                       help='输出 PDF 文件名 (默认: website.pdf)')
    parser.add_argument('-b', '--browser', 
                       choices=['chromium', 'firefox', 'webkit'],
                       default='chromium',
                       help='浏览器类型 (默认: chromium)')
    parser.add_argument('--max-pages', type=int, 
                       help='最大转换页面数')
    parser.add_argument('--no-toc', action='store_true',
                       help='不生成目录页')
    parser.add_argument('--keep-sidebar', action='store_true',
                       help='保留侧边栏和导航栏（默认隐藏）')
    
    args = parser.parse_args()
    
    if not Path(args.httrack_dir).exists():
        logger.error(f"错误: 目录 {args.httrack_dir} 不存在")
        sys.exit(1)
    
    converter = SiteToPDF(
        args.httrack_dir, 
        args.output,
        browser_type=args.browser,
        max_pages=args.max_pages,
        include_toc=not args.no_toc,
        hide_sidebar=not args.keep_sidebar
    )
    
    success = await converter.convert()
    
    if success:
        logger.info("转换完成!")
    else:
        logger.error("转换失败!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
