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
            
            if len(cells) < 5:
                return None
            
            category = cells[0]
            name_cell = cells[1]
            size_cell = cells[2]
            seeders_cell = cells[3]
            leechers_cell = cells[4]
            
            magnet_pattern = r"href='(magnet:[^']+)'"
            magnet_match = re.search(magnet_pattern, name_cell)
            magnet_link = magnet_match.group(1) if magnet_match else ""
            
            name_pattern = r"href='/details\.php\?id=\d+'>([^<]+)</a>"
            name_match = re.search(name_pattern, name_cell)
            name = name_match.group(1) if name_match else "Unknown"
            
            date_pattern = r"<div class='sub'[^>]*>([^<]+)</div>"
            date_match = re.search(date_pattern, name_cell)
            upload_date = date_match.group(1).strip() if date_match else ""
            
            size = re.sub(r'<[^>]+>', '', size_cell).strip()
            
            seeders_text = re.sub(r'<[^>]+>', '', seeders_cell).strip()
            seeders = int(seeders_text.replace(',', '')) if seeders_text.replace(',', '').isdigit() else 0
            
            leechers_text = re.sub(r'<[^>]+>', '', leechers_cell).strip()
            leechers = int(leechers_text.replace(',', '')) if leechers_text.replace(',', '').isdigit() else 0
            
            return {
                "name": name,
                "url": f"{self.base_url}/details.php?id=",
                "magnet": magnet_link,
                "category": "TV" if "TV" in category else "Unknown",
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


def main():
    """Example usage of the MCP service"""
    service = PirateBayMCPService()
    
    # Example search
    print("Searching for 'Ted'...")
    results = service.search("Ted", 1)
    
    print(f"Found {len(results)} results:")
    for i, torrent in enumerate(results[:5]):  # Show first 5 results
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