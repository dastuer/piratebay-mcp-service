# 配置 Agent 使用 Pirate Bay MCP 服务

本文档说明如何将 AI Agent 配置为使用我们实现的 Pirate Bay MCP 服务。

## 前提条件

1. MCP 服务必须已经在运行：
   ```bash
   python3 mcp_server.py
   ```

2. 服务将通过标准输入/输出 (stdio) 通信

## 配置方式

### 方式 1: 通过 MCP 客户端库连接（编程方式）

如果您要通过代码方式让 Agent 使用此服务，可以使用 MCP 客户端库：

```python
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

# 配置服务器参数
server_params = StdioServerParameters(
    command="python3",
    args=["mcp_server.py"],  # 路径到您的 mcp_server.py
    env=None,  # 可选的环境变量
)

# 创建客户端会话
async def run_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化会话
            await session.initialize()
            
            # 列出可用工具
            tools = await session.list_tools()
            print("可用工具:", [tool.name for tool in tools.tools])
            
            # 调用搜索工具
            result = await session.call_tool("search_torrents", {
                "keyword": "Ted S02E01",
                "page": 1
            })
            print("搜索结果:", result.content[0].text)
            
            # 从结果中获取磁力链接并下载
            # （实际使用中需要解析结果获取磁力链接）
            
# 运行 Agent
import asyncio
asyncio.run(run_agent())
```

### 方式 2: 在配置文件中声明 MCP 服务

对于支持 MCP 配置的 Agent 框架，您可以在配置文件中声明此服务：

#### 例子：在 opencode 或类似 Agent 中的配置

```yaml
# agent_config.yaml
mcp_services:
  piratebay:
    command: python3
    args: 
      - /path/to/piratebay-search/mcp_server.py
    env: {}
    # 或者如果使用虚拟环境:
    # command: /path/to/venv/bin/python
    # args: ["/path/to/piratebay-search/mcp_server.py"]
    
    # 服务描述（可选）
    description: "Pirate Bay 搜索和下载服务"
    
    # 工具别名映射（可选）
    tool_aliases:
      search_torrents: "搜索种子"
      download_torrent: "下载种子"
```

### 方式 3: 直接通过命令行交互

一些 Agent 系统允许直接通过命令行与 MCP 服务交互：

```bash
# 启动 MCP 服务并在后台运行
python3 mcp_server.py &

# 然后在 Agent 中，您可以通过特定命令调用工具
# 具体语法取决于您的 Agent 系统
```

## 在 Agent 中使用的示例场景

以下是一个可能的 Agent 交互流程示例：

**用户:** "帮我搜索 Ted 第二季的所有 1080p 版本"

**Agent 思考过程:**
1. 需要使用 search_torrents 工具
2. 关键词应该是 "Ted S02E01" 到 "Ted S02E08" 或者更通用的 "Ted S02"
3. 可能需要分页搜索以获取所有结果

**Agent 行动:**
```python
# 搜索 Ted 第二季
results = await session.call_tool("search_torrents", {
    "keyword": "Ted S02",
    "page": 1
})

# 处理结果，可能需要获取多页
# 解析磁力链接信息
# 向用户展示结果
```

**Agent 回复:**
```
找到以下 Ted 第二季 1080p 版本：
1. Ted S02E01 1080p WEB h264-ETHEL - 大小: 2.14GB, 做种: 263, 下载: 31
   磁力链接: magnet:?xt=urn:btih:...
2. Ted S02E02 1080p WEB h264-ETHEL - 大小: 1.98GB, 做种: 258, 下载: 27
   磁力链接: magnet:?xt=urn:btih:...
...
```

**用户:** "下载第一集"

**Agent 行动:**
```python
# 从之前的结果中提取第一个磁力链接并调用下载工具
magnet_link = "从搜索结果中提取的第一个磁力链接"
await session.call_tool("download_torrent", {
    "magnet_link": magnet_link
})
```

**Agent 回复:**
```
已准备好下载 Ted S02E01 1080p WEB h264-ETHEL
磁力链接: magnet:?xt=urn:btih:...
请使用您的 BT 客户端打开此链接开始下载
```

## 注意事项

1. **服务器生命周期**: 确保在 Agent 使用期间 MCP 服务保持运行状态
2. **错误处理**: Agent 应该处理网络错误、无效响应等情况
3. **结果解析**: 搜索结果返回的是格式化文本，Agent 可能需要解析以提取特定字段
4. **速率限制**: 考虑添加请求间隔以避免过于频繁的搜索
5. **法律合规**: 确保只下载有权限访问的内容

## 故障排除

如果 Agent 无法连接到 MCP 服务：
1. 验证 mcp_server.py 是否可以正常运行：`python3 mcp_server.py`
2. 检查是否有端口冲突（虽然 stdio 不使用端口，但要确保没有其他问题）
3. 确认 Agent 配置中指定的 Python 路径和脚本路径正确
4. 查看 MCP 服务的 stdout/stderr 输出以诊断问题

## 与现有 Agent 框架的集成

不同的 Agent 框架可能有不同的 MCP 集成方式。请参考您所使用的 Agent 框架文档中关于 "MCP 集成"、"工具插件" 或 "外部服务" 的章节。

常见的集成点包括：
- 配置文件中的 `mcp_services` 或 `external_tools` 部分
- 通过命令行参数指定 MCP 服务器
- 在 Agent 初始化时注册 MCP 客户端
- 使用特定的 SDK 或插件机制