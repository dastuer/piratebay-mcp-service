# Pirate Bay MCP Service Configuration

## Installation

1. Install the required dependency:
```bash
python3 -m pip install mcp
```

## Running the Service

To start the MCP server:
```bash
python3 mcp_server.py
```

The server will run over stdio and wait for MCP client connections.

## Configuration Options

### Base URL Configuration

The service currently uses `https://thepiratebay10.xyz` as the base URL. To change this:

1. Modify the `base_url` parameter when instantiating `PirateBayMCPService` in `mcp_server.py`:
```python
# In mcp_server.py, line where service is initialized:
self.service = PirateBayMCPService(base_url="https://your-preferred-proxy.xyz")
```

2. Or set via environment variable (would require modifying the code):
```python
import os
base_url = os.getenv("PIRATEBAY_BASE_URL", "https://thepiratebay10.xyz")
self.service = PirateBayMCPService(base_url=base_url)
```

### MCP Server Configuration

The MCP server uses standard stdio transport. No additional configuration is needed for basic operation.

## Using the MCP Tools

Once the server is running, MCP clients can call two tools:

### 1. search_torrents
Search for torrents on Pirate Bay.

**Parameters:**
- `keyword` (string, required): The search term
- `page` (integer, optional, default: 1): Page number to retrieve

**Example:**
```json
{
  "keyword": "Ted",
  "page": 1
}
```

**Returns:** Formatted text with search results including torrent names, sizes, seeders/leechers, and magnet links.

### 2. download_torrent
Prepare a torrent for download using its magnet link.

**Parameters:**
- `magnet_link` (string, required): Valid magnet URI starting with "magnet:"

**Example:**
```json
{
  "magnet_link": "magnet:?xt=urn:btih:EXAMPLE&dn=example.torrent&tr=..."
}
```

**Returns:** Confirmation that the torrent download has been initiated with the magnet link.

## Example Usage Flow

1. Search for content:
```json
{
  "keyword": "Ted S02E01",
  "page": 1
}
```

2. From the results, copy a magnet link for the desired torrent

3. Initiate download:
```json
{
  "magnet_link": "magnet:?xt=urn:btih:...copied-from-search-results..."
}
```

## Notes

- The service includes browser-like headers and SSL handling to avoid common blocking issues
- Search results are parsed from HTML and returned in a human-readable format
- For automated use, clients should parse the returned text to extract specific torrent details
- Always respect copyright laws and only download content you have the right to access