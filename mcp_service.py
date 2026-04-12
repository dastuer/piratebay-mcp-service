#!/usr/bin/env python3
"""
MCP Service for Pirate Bay and UIndex search and download
"""

import urllib.parse
import urllib.request
import urllib.error
import ssl
import re
import gzip
from typing import List, Dict, Any, Optional
import json


class PirateBayMCPService:
    def __init__(self, base_url: str = "https://thepiratebay10.xyz"):
        self.base_url = base_url
    
    def search(self, keyword: str, page: int = 1) -> List[Dict[str, Any]]:
        """
        Search for torrents on Pirate Bay
        
        Args:
            keyword: Search keyword
            page: Page number (default: 1)
            
        Returns:
            List of torrent dictionaries with structured data
        """
        # URL encode the keyword
        encoded_keyword = urllib.parse.quote(keyword)
        
        # Construct search URL
        url = f"{self.base_url}/search/{encoded_keyword}/{page}/99/0"
        
        try:
            # Create SSL context that doesn't verify certificates (for testing purposes)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create request with browser-like headers to avoid 403 errors
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # Fetch the search results page
            response = urllib.request.urlopen(req, context=ssl_context)
            
            # Handle gzip encoding if present
            content_encoding = response.info().get('Content-Encoding')
            if content_encoding == 'gzip':
                html_content = gzip.decompress(response.read()).decode('utf-8')
            else:
                html_content = response.read().decode('utf-8')
            
            # Parse the HTML to extract torrent information
            torrents = self._parse_search_results(html_content)
            return torrents
            
        except Exception as e:
            print(f"Error searching Pirate Bay: {e}")
            return []
    
    def _parse_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse HTML search results to extract torrent information
        
        Args:
            html_content: Raw HTML content from search results
            
        Returns:
            List of torrent dictionaries
        """
        torrents = []
        
        # Find the main table with search results
        # Look for the table with id="searchResult"
        table_pattern = r'<table[^>]*id=["\']searchResult["\'][^>]*>(.*?)</table>'
        table_match = re.search(table_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        if not table_match:
            # Alternative pattern if id is not exactly matched
            table_pattern = r'<table[^>]*class=["\'][^"\']*searchResult[^"\']*["\'][^>]*>(.*?)</table>'
            table_match = re.search(table_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        if not table_match:
            return torrents
        
        table_content = table_match.group(1)
        
        # Find all rows in the table body (skip header)
        # Look for tr tags that are not in thead
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        rows = re.findall(row_pattern, table_content, re.DOTALL | re.IGNORECASE)
        
        # Skip the first row if it's the header (contains th tags)
        for i, row in enumerate(rows):
            if i == 0 and '<th' in row:
                continue
                
            torrent = self._parse_torrent_row(row)
            if torrent:
                torrents.append(torrent)
        
        return torrents
    
    def _parse_torrent_row(self, row_html: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single torrent row from HTML
        
        Args:
            row_html: HTML content of a table row
            
        Returns:
            Dictionary with torrent information or None if parsing fails
        """
        # Extract all td cells
        cell_pattern = r'<td[^>]*>(.*?)</td>'
        cells = re.findall(cell_pattern, row_html, re.DOTALL | re.IGNORECASE)
        
        # Need at least 6 cells for basic info
        if len(cells) < 6:
            return None
        
        try:
            # Parse each cell based on position (from the example HTML)
            # Cell 0: Type (with category link)
            # Cell 1: Name (with torrent link)
            # Cell 2: Upload date
            # Cell 3: (empty or category icons)
            # Cell 4: Size
            # Cell 5: Seeders
            # Cell 6: Leechers
            # Cell 7: Uploader
            
            # Extract type/category
            type_cell = cells[0]
            type_link_pattern = r'<a[^>]*href=["\']([^"\']*)["\'][^>]*title=["\'][^"\']*["\']>[^<]*</a>'
            type_match = re.search(type_link_pattern, type_cell)
            category_url = type_match.group(1) if type_match else ""
            
            # Extract torrent name and URL
            name_cell = cells[1]
            name_link_pattern = r'<a[^>]*href=["\']([^"\']*\/torrent\/[^"\']*)["\'][^>]*title=["\']([^"\']*)["\'][^>]*>([^<]*)</a>'
            name_match = re.search(name_link_pattern, name_cell)
            if not name_match:
                return None
                
            torrent_url = self.base_url + name_match.group(1) if name_match.group(1).startswith('/') else name_match.group(1)
            torrent_title = name_match.group(2)
            display_name = name_match.group(3) if name_match.group(3) else torrent_title
            
            # Extract magnet link (usually in cell 3 or 4)
            magnet_link = ""
            magnet_pattern = r'href=["\'](magnet:[^"\']*)["\']'
            magnet_matches = re.findall(magnet_pattern, row_html)
            if magnet_matches:
                magnet_link = magnet_matches[0]
            
            # Extract upload date (cell 2)
            upload_date = re.sub(r'<[^>]+>', '', cells[2]).strip()
            
            # Extract size (cell 4)
            size_cell = cells[4]
            size = re.sub(r'<[^>]+>', '', size_cell).strip()
            
            # Extract seeders (cell 5)
            seeders_cell = cells[5]
            seeders_text = re.sub(r'<[^>]+>', '', seeders_cell).strip()
            seeders = int(seeders_text) if seeders_text.isdigit() else 0
            
            # Extract leechers (cell 6)
            leechers_cell = cells[6] if len(cells) > 6 else ""
            leechers_text = re.sub(r'<[^>]+>', '', leechers_cell).strip()
            leechers = int(leechers_text) if leechers_text.isdigit() else 0
            
            # Extract uploader (cell 7)
            uploader_cell = cells[7] if len(cells) > 7 else ""
            uploader_link_pattern = r'<a[^>]*href=["\']([^"\']*\/user\/[^"\']*)["\'][^>]*>([^<]*)</a>'
            uploader_match = re.search(uploader_link_pattern, uploader_cell)
            uploader = uploader_match.group(2) if uploader_match else ""
            uploader_url = self.base_url + uploader_match.group(1) if uploader_match and uploader_match.group(1).startswith('/') else (uploader_match.group(1) if uploader_match else "")
            
            return {
                "name": display_name,
                "title": torrent_title,
                "url": torrent_url,
                "magnet": magnet_link,
                "category": category_url,
                "upload_date": upload_date,
                "size": size,
                "seeders": seeders,
                "leechers": leechers,
                "uploader": uploader,
                "uploader_url": uploader_url
            }
            
        except Exception as e:
            print(f"Error parsing torrent row: {e}")
            return None
    
    def download_torrent(self, magnet_link: str) -> bool:
        """
        Prepare a torrent for download by copying the magnet link to clipboard
        
        Args:
            magnet_link: Magnet URI for the torrent
            
        Returns:
            True if the link is valid and copied to clipboard, False otherwise
        """
        import subprocess
        import platform
        
        if not magnet_link or not magnet_link.startswith("magnet:"):
            print(f"Invalid magnet link: {magnet_link}")
            return False
        
        try:
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["pbcopy"], input=magnet_link.encode(), check=True)
            elif system == "Linux":  # Linux
                # Try xclip first, then xsel
                try:
                    subprocess.run(["xclip", "-selection", "clipboard"], input=magnet_link.encode(), check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    subprocess.run(["xsel", "--clipboard", "--input"], input=magnet_link.encode(), check=True)
            elif system == "Windows":  # Windows
                subprocess.run(["clip"], input=magnet_link.encode(), check=True)
            else:
                # Fallback: just print the link
                print(f"Magnet link (copy manually): {magnet_link}")
                return True
            
            print(f"Magnet link copied to clipboard: {magnet_link[:60]}...")
            return True
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")
            print(f"Magnet link (copy manually): {magnet_link}")
            return True  # Still return True as the link is valid


class UIndexMCPService:
    """MCP Service for UIndex search and download"""
    
    def __init__(self, base_url: str = "https://uindex.org"):
        self.base_url = base_url
    
    def search(self, keyword: str, category: int = 0) -> List[Dict[str, Any]]:
        """
        Search for torrents on UIndex
        
        Args:
            keyword: Search keyword
            category: Category ID (0 = all, 2 = TV, etc.)
            
        Returns:
            List of torrent dictionaries with structured data
        """
        encoded_keyword = urllib.parse.quote(keyword)
        url = f"{self.base_url}/search.php?search={encoded_keyword}&c={category}"
        
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
            )
            
            response = urllib.request.urlopen(req, context=ssl_context)
            content_encoding = response.info().get('Content-Encoding')
            if content_encoding == 'gzip':
                html_content = gzip.decompress(response.read()).decode('utf-8')
            else:
                html_content = response.read().decode('utf-8')
            
            torrents = self._parse_search_results(html_content)
            return torrents
            
        except Exception as e:
            print(f"Error searching UIndex: {e}")
            return []

    def _parse_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse HTML search results to extract torrent information"""
        torrents = []

        tbody_pattern = r'<tbody>(.*?)</tbody>'
        tbody_match = re.search(tbody_pattern, html_content, re.DOTALL | re.IGNORECASE)
        if not tbody_match:
            return torrents

        tbody_content = tbody_match.group(1)
        row_pattern = r'<tr>(.*?)</tr>'
        rows = re.findall(row_pattern, tbody_content, re.DOTALL | re.IGNORECASE)

        for row in rows:
            torrent = self._parse_torrent_row(row)
            if torrent:
                torrents.append(torrent)

        return torrents

    def _parse_torrent_row(self, row_html: str) -> Optional[Dict[str, Any]]:
        """Parse a single torrent row from HTML"""
        try:
            cell_pattern = r'<td[^>]*>(.*?)</td>'
            cells = re.findall(cell_pattern, row_html, re.DOTALL | re.IGNORECASE)

            # 现有的 HTML 结构至少有 6 列: Cat, Name, Size, Uploaded, S, L
            if len(cells) < 6:
                return None

            category_cell = cells[0]
            name_cell = cells[1]
            size_cell = cells[2]
            date_cell = cells[3]  # 上传时间独立成了一列
            seeders_cell = cells[4]
            leechers_cell = cells[5]

            # 获取分类 (清理 SVG 和 HTML 标签)
            category = re.sub(r'<[^>]+>', '', category_cell).strip()

            # 提取 Magnet Link (适配双引号)
            magnet_pattern = r'href="(magnet:[^"]+)"'
            magnet_match = re.search(magnet_pattern, name_cell)
            # 替换 HTML 转义字符保证 magnet 链接有效
            magnet_link = magnet_match.group(1).replace('&amp;', '&') if magnet_match else ""

            # 提取详情页 ID
            id_pattern = r'href="/details\.php\?id=(\d+)"'
            id_match = re.search(id_pattern, name_cell)
            torrent_id = id_match.group(1) if id_match else ""

            # 提取名称: 直接使用 title 属性，避免 <mark> 标签干扰
            name_pattern = r'class="sr-torrent-link"[^>]*title="([^"]+)"'
            name_match = re.search(name_pattern, name_cell)
            if name_match:
                name = name_match.group(1).strip()
            else:
                # 兜底方案：直接剥离所有的 HTML 标签
                link_content_match = re.search(r'class="sr-torrent-link"[^>]*>(.*?)</a>', name_cell, re.DOTALL)
                if link_content_match:
                    name = re.sub(r'<[^>]+>', '', link_content_match.group(1)).strip()
                else:
                    name = "Unknown"

            # 提取上传时间
            upload_date = re.sub(r'<[^>]+>', '', date_cell).strip()

            # 提取文件大小
            size = re.sub(r'<[^>]+>', '', size_cell).strip()

            # 提取做种数
            seeders_text = re.sub(r'<[^>]+>', '', seeders_cell).strip()
            seeders = int(seeders_text.replace(',', '')) if seeders_text.replace(',', '').isdigit() else 0

            # 提取吸血数
            leechers_text = re.sub(r'<[^>]+>', '', leechers_cell).strip()
            leechers = int(leechers_text.replace(',', '')) if leechers_text.replace(',', '').isdigit() else 0

            return {
                "name": name,
                "url": f"{self.base_url}/details.php?id={torrent_id}" if torrent_id else "",
                "magnet": magnet_link,
                "category": category if category else "Unknown",
                "upload_date": upload_date,
                "size": size,
                "seeders": seeders,
                "leechers": leechers,
                "uploader": "UIndex",
                "uploader_url": ""
            }

        except Exception as e:
            print(f"Error parsing UIndex torrent row: {e}")
            return None
     
    def download_torrent(self, magnet_link: str) -> bool:
        """Copy magnet link to clipboard for download"""
        import subprocess
        import platform
        
        if not magnet_link or not magnet_link.startswith("magnet:"):
            print(f"Invalid magnet link: {magnet_link}")
            return False
        
        try:
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["pbcopy"], input=magnet_link.encode(), check=True)
            elif system == "Linux":
                try:
                    subprocess.run(["xclip", "-selection", "clipboard"], input=magnet_link.encode(), check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    subprocess.run(["xsel", "--clipboard", "--input"], input=magnet_link.encode(), check=True)
            elif system == "Windows":
                subprocess.run(["clip"], input=magnet_link.encode(), check=True)
            else:
                print(f"Magnet link (copy manually): {magnet_link}")
                return True
            
            print(f"Magnet link copied to clipboard: {magnet_link[:60]}...")
            return True
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")
            print(f"Magnet link (copy manually): {magnet_link}")
            return True


class SoubtsouMCPService:
    """MCP Service for Soubtsou search and download"""
    
    def __init__(self, base_url: str = "https://www.soubtsou.blog"):
        self.base_url = base_url
    
    def _utf16to8(self, s: str) -> str:
        """Convert UTF-16 to UTF-8 encoding"""
        out = ""
        len_s = len(s)
        for i in range(len_s):
            c = ord(s[i])
            if (c >= 0x0001) and (c <= 0x007F):
                out += s[i]
            elif c > 0x07FF:
                out += chr(0xE0 | ((c >> 12) & 0x0F))
                out += chr(0x80 | ((c >> 6) & 0x3F))
                out += chr(0x80 | ((c >> 0) & 0x3F))
            else:
                out += chr(0xC0 | ((c >> 6) & 0x1F))
                out += chr(0x80 | ((c >> 0) & 0x3F))
        return out
    
    def _str2hex(self, s: str) -> str:
        """Convert string to hex representation"""
        val = ""
        for i in range(len(s)):
            val += "{:x}".format(ord(s[i]))
        return val
    
    def _build_search_url(self, keyword: str, page: int = 1) -> str:
        """Build search URL for Soubtsou based on their JavaScript logic"""
        # Process keyword like their mysubmit function:
        # value = str2hex(utf16to8(document.getElementById('search').value));
        processed = self._str2hex(self._utf16to8(keyword))
        url = f"{self.base_url}/btsousuo/{processed}-{page}-id.html"
        return url
    
    def search(self, keyword: str, page: int = 1) -> List[Dict[str, Any]]:
        """
        Search for torrents on Soubtsou
        
        Args:
            keyword: Search keyword
            page: Page number (default: 1)
            
        Returns:
            List of torrent dictionaries with structured data
        """
        if not keyword:
            return []
        
        # For pagination, Soubtsou uses different URLs like:
        # /btsousuo/[value]-2-id.html for page 2
        url = self._build_search_url(keyword, page)
        
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                }
            )
            
            response = urllib.request.urlopen(req, context=ssl_context)
            content_encoding = response.info().get('Content-Encoding')
            if content_encoding == 'gzip':
                html_content = gzip.decompress(response.read()).decode('utf-8')
            else:
                html_content = response.read().decode('utf-8')
            
            torrents = self._parse_search_results(html_content)
            return torrents
            
        except Exception as e:
            print(f"Error searching Soubtsou: {e}")
            return []
    
    def _parse_search_results(self, html_content: str) -> List[Dict[str, Any]]:
        """Parse HTML search results to extract torrent information"""
        torrents = []
        
        # Find all related-article divs
        # The HTML might have extra whitespace or different formatting
        article_pattern = r'<div class="related-article">.*?</div>'
        articles = re.findall(article_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        for article in articles:
            torrent = self._parse_torrent_article(article)
            if torrent:
                torrents.append(torrent)
        
        return torrents

    def _parse_torrent_article(self, article_html: str) -> Optional[Dict[str, Any]]:
        """Parse a single torrent article from HTML"""
        try:
            # 修改点 1: 将 ([^<]+) 改为 ([\s\S]*?) 以匹配内部的 <mark> 等 HTML 标签
            title_pattern = r'<h1[^>]*class="[^"]*article-title[^"]*"[^>]*>\s*<a\s+href="([^"]+)">([\s\S]*?)</a>'
            title_match = re.search(title_pattern, article_html)

            if not title_match:
                return None

            relative_url = title_match.group(1)
            title_html = title_match.group(2)

            # 修改点 2: 使用泛用正则清理掉标题内所有的 HTML 标签 (包括 <mark>)
            clean_title = re.sub(r'<[^>]+>', '', title_html).strip()

            # Build full URL
            if relative_url.startswith('/'):
                torrent_url = f"{self.base_url}{relative_url}"
            else:
                torrent_url = f"{self.base_url}/{relative_url}"

            # Extract magnet hash from the detail page URL
            magnet_hash_match = re.search(r'/btxiazai/([a-f0-9]+)\.html', relative_url, re.IGNORECASE)
            if magnet_hash_match:
                magnet_hash = magnet_hash_match.group(1)
                magnet_link = f"magnet:?xt=urn:btih:{magnet_hash}"
            else:
                magnet_link = ""

            # 修改点 3: 优化 meta_pattern 适配 HTML 里的换行和空格结构
            meta_pattern = r'<div[^>]*class="[^"]*article-meta[^"]*"[^>]*>\s*<p>类型：<b>([^<]+)</b>\s*大小：<b>([^<]+)</b>\s*数量：<b>([^<]+)</b>\s*时间：<b>([^<]+)</b></p>'
            meta_match = re.search(meta_pattern, article_html)

            file_type = meta_match.group(1) if meta_match else "未知"
            size = meta_match.group(2) if meta_match else "未知"
            count = meta_match.group(3) if meta_match else "0"
            upload_date = meta_match.group(4) if meta_match else "未知"

            return {
                "name": clean_title,
                "url": torrent_url,
                "magnet": magnet_link,
                "category": file_type.strip(),
                "upload_date": upload_date.strip(),
                "size": size.strip(),
                "seeders": 0,  # Not available in search results
                "leechers": 0,  # Not available in search results
                "uploader": "Soubtsou",
                "uploader_url": ""
            }

        except Exception as e:
            print(f"Error parsing Soubtsou torrent article: {e}")
            return None
    
    def download_torrent(self, magnet_link: str) -> bool:
        """Copy magnet link to clipboard for download"""
        import subprocess
        import platform
        
        if not magnet_link or not magnet_link.startswith("magnet:"):
            print(f"Invalid magnet link: {magnet_link}")
            return False
        
        try:
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["pbcopy"], input=magnet_link.encode(), check=True)
            elif system == "Linux":
                try:
                    subprocess.run(["xclip", "-selection", "clipboard"], input=magnet_link.encode(), check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    subprocess.run(["xsel", "--clipboard", "--input"], input=magnet_link.encode(), check=True)
            elif system == "Windows":
                subprocess.run(["clip"], input=magnet_link.encode(), check=True)
            else:
                print(f"Magnet link (copy manually): {magnet_link}")
                return True
            
            print(f"Magnet link copied to clipboard: {magnet_link[:60]}...")
            return True
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")
            print(f"Magnet link (copy manually): {magnet_link}")
            return True


def main():
    """Example usage of the MCP service"""
    service = UIndexMCPService()
    
    # Example search
    print("Searching for 'Ted'...")
    results = service.search("Ted", 1)
    
    print(f"Found {len(results)} results:")
    for i, torrent in enumerate(results[:10]):  # Show first 5 results
        print(f"{i+1}. {torrent['name']}")
        print(f"   Size: {torrent['size']}, Seeders: {torrent['seeders']}, Leechers: {torrent['leechers']}")
        print(f"   Magnet: {torrent['magnet'][:50]}..." if torrent['magnet'] else "   No magnet link")
        print()
    
    # Example download (if we have results)
    if results and results[0].get('magnet'):
        print("Preparing to download first result...")
        service.download_torrent(results[0]['magnet'])


if __name__ == "__main__":
    main()