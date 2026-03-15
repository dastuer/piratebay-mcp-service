#!/usr/bin/env python3
"""
MCP Server for Pirate Bay and UIndex search and download service
Provides search and download tools as MCP endpoints
"""

import asyncio
import signal
import sys
from typing import Any, List, Dict
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp_service import PirateBayMCPService, UIndexMCPService

max_page_count=100

class MultiSiteMCPServer:
    def __init__(self):
        self.piratebay_service = PirateBayMCPService()
        self.uindex_service = UIndexMCPService()
        self.server = Server("multi-site-search")
        
        # Set up tool handlers using decorators
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="search_piratebay",
                    description="Search for torrents on Pirate Bay",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string", "description": "Search term"},
                            "page": {"type": "integer", "description": "Page number (default: 1)", "default": 1}
                        },
                        "required": ["keyword"]
                    }
                ),
                Tool(
                    name="search_uindex",
                    description="Search for torrents on UIndex",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keyword": {"type": "string", "description": "Search term"},
                            "category": {"type": "integer", "description": "Category ID (0 = all, 2 = TV, etc.)", "default": 0}
                        },
                        "required": ["keyword"]
                    }
                ),
                Tool(
                    name="download_torrent",
                    description="Prepare a torrent for download using its magnet link",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "magnet_link": {"type": "string", "description": "Valid magnet URI starting with 'magnet:'"}
                        },
                        "required": ["magnet_link"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            if name == "search_piratebay":
                return await self.search_piratebay(arguments)
            elif name == "search_uindex":
                return await self.search_uindex(arguments)
            elif name == "download_torrent":
                return await self.download_torrent(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def search_piratebay(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Search for torrents on Pirate Bay
        
        Expected arguments:
        {
            "keyword": "search term",
            "page": 1  (optional, default: 1)
        }
        """
        keyword = arguments.get("keyword", "")
        page = arguments.get("page", 1)
        
        if not keyword:
            return [TextContent(type="text", text="Error: keyword is required")]
        
        try:
            results = self.piratebay_service.search(keyword, page)
            
            if not results:
                return [TextContent(type="text", text="No results found")]
            
            # Format results as readable text
            output = f"Found {len(results)} Pirate Bay results for '{keyword}' (page {page}):\n\n"
            
            for i, torrent in enumerate(results[:max_page_count]):  # Limit to 10 results
                output += f"{i+1}. {torrent['name']}\n"
                output += f"   Size: {torrent['size']} | Seeders: {torrent['seeders']} | Leechers: {torrent['leechers']}\n"
                output += f"   Uploaded: {torrent['upload_date']} | Uploader: {torrent['uploader']}\n"
                if torrent['magnet']:
                    output += f"   Magnet: {torrent['magnet'][:60]}...\n"
                output += "\n"
            
            if len(results) > max_page_count:
                output += f"... and {len(results) - max_page_count} more results\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error searching Pirate Bay: {str(e)}")]
    
    async def search_uindex(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Search for torrents on UIndex
        
        Expected arguments:
        {
            "keyword": "search term",
            "category": 0  (optional, default: 0)
        }
        """
        keyword = arguments.get("keyword", "")
        category = arguments.get("category", 0)
        
        if not keyword:
            return [TextContent(type="text", text="Error: keyword is required")]
        
        try:
            results = self.uindex_service.search(keyword, category)
            
            if not results:
                return [TextContent(type="text", text="No results found")]
            
            # Format results as readable text
            output = f"Found {len(results)} UIndex results for '{keyword}' (category {category}):\n\n"
            
            for i, torrent in enumerate(results[:max_page_count]):  # Limit to 10 results
                output += f"{i+1}. {torrent['name']}\n"
                output += f"   Size: {torrent['size']} | Seeders: {torrent['seeders']} | Leechers: {torrent['leechers']}\n"
                output += f"   Uploaded: {torrent['upload_date']} | Uploader: {torrent['uploader']}\n"
                if torrent['magnet']:
                    output += f"   Magnet: {torrent['magnet'][:60]}...\n"
                output += "\n"
            
            if len(results) > max_page_count:
                output += f"... and {len(results) - max_page_count} more results\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error searching UIndex: {str(e)}")]
    
    async def download_torrent(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Prepare a torrent for download using its magnet link
        
        Expected arguments:
        {
            "magnet_link": "magnet:?xt=..."
        }
        """
        magnet_link = arguments.get("magnet_link", "")
        
        if not magnet_link:
            return [TextContent(type="text", text="Error: magnet_link is required")]
        
        if not magnet_link.startswith("magnet:"):
            return [TextContent(type="text", text="Error: Invalid magnet link")]
        
        try:
            # Try both services - they have the same download_torrent implementation
            success = self.piratebay_service.download_torrent(magnet_link)
            if success:
                return [TextContent(type="text", text=f"Torrent download initiated:\n{magnet_link}")]
            else:
                return [TextContent(type="text", text="Error: Failed to initiate download")]
                
        except Exception as e:
            return [TextContent(type="text", text=f"Error preparing download: {str(e)}")]
    
    async def run(self):
        """Run the MCP server"""
        # Set up signal handlers for graceful shutdown
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
    
    async def shutdown(self):
        """Graceful shutdown"""
        pass


def main():
    """Main entry point"""
    server = MultiSiteMCPServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()