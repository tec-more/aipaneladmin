# RAG 集成完整说明

## 概述

本项目现在支持三种方式：

1. **pgvector 方式（推荐！）** - 使用 PostgreSQL pgvector 扩展存储向量，数据库内置索引搜索
2. **LlmaIndex + Qdrant 方式** - 使用 LlamaIndex 管理，Qdrant 作为向量数据库
3. **简易方式（兼容）** - 使用 PostgreSQL BYTEA 存储向量，内存计算相似度

## 快速开始

### 第一步：安装依赖

```bash
pip install -r requirements.txt
```

新增的依赖：
- llama-index
- llama-index-vector-stores-qdrant
- qdrant-client

# 文档解析依赖
- pdfplumber - PDF解析
- python-docx - Word解析
- openpyxl - Excel解析
- python-pptx - PPT解析
- pypdf - PDF解析备选
- pandas - 表格处理

### 第二步（推荐）：运行 pgvector 迁移

```bash
python migrate_pgvector.py
```

这将：
1. 启用 pgvector 扩展
2. 添加 vector_pg 列到 rag_document_chunk 表
3. 提供创建索引的指导

### 第二步：启动 Qdrant（可选，如果用 LlamaIndex 方式）

最简单的方式是用 Docker：

```bash
docker run -p 6333:6333 -p 6334:6334 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant:latest
```

或者从官方下载二进制文件运行。

### 第三步：运行数据库迁移

```bash
# 第一次：添加 node_id 字段
python migrate_add_node_id.py
```

### 第四步：配置 LLM 模型

1. 进入 LLM 管理
2. 添加一个模型（支持 OpenAI 兼容接口）
3. 为该模型添加 API Key 并设为激活

### 第五步：创建知识库

1. 进入智能体管理 -> RAG
2. 点击新建知识库
3. 选择刚才配置的 Embedding 模型
4. 保存

### 第六步：添加和处理文档

1. 选择知识库
2. 上传文档或手动添加
3. 点击"处理文档"按钮
4. 等待处理完成

## 支持的文件格式

现在支持丰富的文档格式：

### 办公文档
| 格式 | 扩展名 | 说明 |
|------|--------|------|
| **PDF** | `.pdf` | 支持文本提取，需要安装 pdfplumber |
| **Word** | `.docx` | 支持段落和表格，需要安装 python-docx |
| **Excel** | `.xlsx` | 支持多 Sheet，需要安装 pandas + openpyxl |
| **PPT** | `.pptx` | 支持文本和备注，需要安装 python-pptx |

### 文本与代码
| 格式 | 扩展名 |
|------|--------|
| **纯文本** | `.txt` |
| **Markdown** | `.md` |
| **Python** | `.py` |
| **JavaScript** | `.js` |
| **HTML/CSS** | `.html`, `.css` |
| **JSON/YAML** | `.json`, `.yaml`, `.yml` |

### 文件上传说明
1. 拖拽或点击选择文件
2. 系统会自动解析文件内容
3. 然后点击"处理文档"进行向量化

---

## 三种使用方式

### 方式 A：pgvector 方式（强烈推荐！）

使用 PostgreSQL pgvector 扩展：

```javascript
// 前端调用时设置
processRAGDocument(docId, 500, 50, 'smart', false) // 不需要 LlamaIndex
// 搜索时使用 pgvector
searchRAG(searchData, false, true)
```

特点：
- 无需额外服务！
- 完全集成在现有的 PostgreSQL 中
- 支持向量索引（ANN 搜索）
- 适合中小规模（< 100,000 条）
- 查询速度快！

### 方式 B：LlamaIndex + Qdrant 方式

使用 LlamaIndex 管理，Qdrant 存储：

```javascript
// 前端调用时设置
processRAGDocument(docId, 500, 50, 'smart', true)
```

特点：
- 需要 Qdrant 服务
- 功能强大，支持复杂的 RAG pipeline
- 适合大规模（> 100,000 条）

### 方式 C：简易方式（兼容）

使用内存搜索（最慢）：

```javascript
// 前端调用时设置
processRAGDocument(docId, 500, 50, 'smart', false)
searchRAG(searchData, false, false) // 禁用 pgvector
```

特点：
- 无需额外服务
- 适合极少量文档（< 1000 条）
- 查询速度慢

### 方式 B：高性能方式（推荐）

使用 Qdrant + LlamaIndex：

```javascript
// 前端调用时使用默认设置
processRAGDocument(docId, 500, 50, 'smart', true)
```

特点：
- 需要运行 Qdrant
- 适合大量文档（> 1000 片段）
- 查询快速，支持 ANN 搜索

## 架构说明

### pgvector 架构设计（推荐！）

```
┌─────────────────────────────────────────────────────────┐
│                    PostgreSQL                             │
│  ┌──────────────────┐  ┌─────────────────────────────────┐│
│  │ Knowledge Base   │  │ Document (doc info)             ││
│  └──────────────────┘  └─────────────────────────────────┘│
│  ┌──────────────────────────────────────────────────────┐│
│  │ Document Chunk (with vector_pg for pgvector!)        ││
│  └──────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

**数据流向（pgvector 方式）：**

文档处理时：
```
文档 → PostgreSQL（保存内容）
     → 向量化 → vector（保持兼容）和 vector_pg（pgvector）
```

搜索时：
```
查询 → 向量化 → 使用 pgvector 的 <=> 操作符搜索
       → 返回最相关结果
```

### 混合架构设计（LlmaIndex 方式）

```
┌─────────────────────────────────────────────────────────┐
│                    PostgreSQL                             │
│  ┌──────────────────┐  ┌─────────────────────┐         │
│  │ Knowledge Base   │  │ Document (doc info) │         │
│  └──────────────────┘  └─────────────────────┘         │
│  ┌─────────────────────────────────────────────┐        │
│  │ Document Chunk (with node_id)              │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  LlamaIndex Adapter + Qdrant Vector DB                  │
│  ┌─────────────────────────────────────────────┐        │
│  │  Qdrant Collection (one per KB)            │        │
│  └─────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────┘
```

### 数据流向

**文档处理时：**
```
文档 → PostgreSQL（保存内容）→ LlamaIndex（向量化）→ Qdrant（存储向量索引）
```

**搜索时：**
```
查询 → 向量化 → Qdrant 相似度搜索 → PostgreSQL（获取完整信息）→ 返回结果
```

## API 使用说明

### 后端配置

可以在环境变量中设置：

```env
# Qdrant 地址
QDRANT_HOST=http://localhost:6333

# 是否默认使用 LlamaIndex
RAG_USE_LLAMA_INDEX=true
```

### 文档处理 API

```http
POST /api/v1/agent/rag/documents/{doc_id}/process?use_llama_index=true
```

参数说明：
- chunk_size: 分片大小（字符数）
- chunk_overlap: 重叠字符数
- split_strategy: 分片策略（smart/paragraph/simple）
- use_llama_index: 是否使用 LlamaIndex（默认 true）

### 搜索 API

```http
POST /api/v1/agent/rag/search?use_llama_index=true
```

请求体：
```json
{
  "knowledge_base_id": 1,
  "query": "你的搜索问题",
  "top_k": 5
}
```

## 文件格式支持

当前支持纯文本格式文件：
- .txt - 纯文本
- .md - Markdown
- .py, .js 等代码文件

后续可以扩展支持：
- PDF（需要 PyMuPDF）
- Word（需要 python-docx）
- 其他文档格式

## 性能建议

### 文档数量

| 文档数 | 分片数 | 推荐方式 |
|------|--------|--------|
| <50本 | <1000片 | 简易方式 |
| 50-200本 | 1000-5000片 | Qdrant |
| >200本 | >5000片 | 云服务 Qdrant |

### 分片大小

| 文档类型 | 推荐分片大小 |
|--------|-----------|
| 短文档（博客文章） | 500-1000 字符 |
| 中等文档（技术文档） | 1000-2000 字符 |
| 长文档（书籍） | 2000-4000 字符 |

## 常见问题

### 1. Qdrant 连接不上

检查 Qdrant 是否运行：

```bash
curl http://localhost:6333
```

### 2. API Key 错误

确保在 LLM 管理中已正确配置 API Key，并且是激活状态。

### 3. 查询超时

建议：
- 使用 Qdrant 方式
- 检查前端请求超时设置（已设为 5 分钟）

### 4. 迁移现有数据

如果之前已有知识库，可以重新处理文档即可：

```javascript
// 前端可以做个批量操作
for (doc of docs) {
  await processRAGDocument(doc.id, 500, 50, 'smart', true)
}
```

## 后续优化建议

1. 添加更多文档格式解析（PDF, Word 等）
2. 实现混合搜索（关键词 + 向量）
3. 添加搜索结果重排功能
4. 优化分片策略，按语义分块
5. 支持向量数据库的分布式部署

## 相关文件

- `base/plugins/agent/models/rag.py` - RAG 数据模型
- `base/plugins/agent/services/rag_service.py` - RAG 核心服务
- `base/plugins/agent/services/llama_index_adapter.py` - LlamaIndex 适配器
- `base/plugins/agent/services/embedding_factory.py` - Embedding 工厂
- `web/src/views/agent/rag/index.vue` - RAG 前端页面
