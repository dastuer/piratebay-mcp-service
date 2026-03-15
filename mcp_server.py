#!/usr/bin/env python3
"""
MCP Server for Pirate Bay search and download service
Provides search and download tools as MCP endpoints
"""

import asyncio
import signal
import sys
from typing import Any, List, Dict
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from mcp_service import PirateBayMCPService


class PirateBayMCPServer:
    def __init__(self):
        self.service = PirateBayMCPService()
        self.server = Server("piratebay-search")
        
        # Set up tool handlers using decorators
        self._setup_handlers()
    
    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="search_torrents",
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
            if name == "search_torrents":
                return await self.search_torrents(arguments)
            elif name == "download_torrent":
                return await self.download_torrent(arguments)
            else:
                raise ValueError(f"Unknown tool: {name}")
    
    async def search_torrents(self, arguments: Dict[str, Any]) -> List[TextContent]:
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
            results = self.service.search(keyword, page)
            
            if not results:
                return [TextContent(type="text", text="No results found")]
            
            # Format results as readable text
            output = f"Found {len(results)} results for '{keyword}' (page {page}):\n\n"
            
            for i, torrent in enumerate(results[:100]):  # Limit to 10 results
                output += f"{i+1}. {torrent['name']}\n"
                output += f"   Size: {torrent['size']} | Seeders: {torrent['seeders']} | Leechers: {torrent['leechers']}\n"
                output += f"   Uploaded: {torrent['upload_date']} | Uploader: {torrent['uploader']}\n"
                if torrent['magnet']:
                    output += f"   Magnet: {torrent['magnet'][:60]}...\n"
                output += "\n"
            
            if len(results) > 100:
                output += f"... and {len(results) - 100} more results\n"
            
            return [TextContent(type="text", text=output)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error searching: {str(e)}")]
    
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
            success = self.service.download_torrent(magnet_link)
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
    server = PirateBayMCPServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()