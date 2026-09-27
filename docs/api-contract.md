# API 契约基线

基础地址：`/api/v1`。FastAPI OpenAPI 与后端 Pydantic Schema 是接口契约的事实来源。

## 通用约定

- ID 使用 UUID 字符串。
- 时间使用带时区的 ISO 8601 字符串。
- 未实现接口在基础阶段返回 HTTP 501，方法、路径和请求 Schema 不再改变。
- 错误响应：`{ "detail": "..." }`。

## 端点

| 方法 | 路径 | 用途 | 实现阶段 |
| --- | --- | --- | --- |
| GET | `/health` | 服务及数据库健康检查 | 基础 |
| GET | `/model/status` | LLM 与 Embedding 连接状态 | Phase 1 |
| GET | `/knowledge` | 知识库列表 | Phase 1 |
| POST | `/knowledge` | 创建知识库 | Phase 1 |
| DELETE | `/knowledge/{id}` | 删除知识库 | Phase 1 |
| GET | `/documents` | 文档列表 | Phase 2 |
| POST | `/documents/upload` | 上传 PDF/TXT/Markdown | Phase 2 |
| GET | `/documents/{id}` | 获取文档详情 | 增强 |
| GET | `/documents/{id}/content` | 预览原始文件 | 增强 |
| GET | `/documents/{id}/chunks` | 列出文档的 Chunk | 增强 |
| DELETE | `/documents/{id}` | 删除文档 | Phase 2 |
| GET | `/documents/{document_id}/chunks/{chunk_id}` | 获取引用 Chunk 原文 | Phase 6 |
| POST | `/chat` | JSON 或 SSE 聊天响应 | Phase 3 / Phase 5 |
| GET | `/conversations` | 会话列表 | Phase 7 |
| GET | `/conversations/{id}` | 会话详情与消息 | Phase 7 |
| DELETE | `/conversations/{id}` | 删除会话 | Phase 7 |
| GET | `/settings` | 获取设置，API Key 只返回是否已配置 | Phase 1 |
| PUT | `/settings` | 更新设置 | Phase 1 |
| POST | `/settings/test-model` | 测试当前表单中的 LLM / Embedding 连接与 Embedding 维度 | 连接测试 |
| GET | `/indexes` | 列出索引版本与当前激活索引 | 索引版本化 |
| POST | `/indexes/rebuild` | 后台使用当前 Embedding 配置构建新索引 | 索引版本化 |
| POST | `/indexes/{id}/activate` | 验证后切换到指定索引版本 | 索引版本化 |
| POST | `/knowledge/search` | Agent 结构化知识检索 | Phase 8 |

索引重建不会覆盖当前激活索引。新索引只有在所有文档处理成功，且片段数量、
向量维度校验通过后，才允许调用激活接口切换。

## Chat 请求

```json
{
  "message": "RAG 为什么需要 Reranker？",
  "conversation_id": null,
  "knowledge_base_id": null,
  "allow_general_fallback": false,
  "top_k": 5
}
```

## Chat JSON 响应

```json
{
  "conversation_id": "uuid",
  "answer": "回答内容",
  "route": "knowledge",
  "citations": []
}
```

Phase 5 的 SSE 事件类型固定为：

```text
search_status
answer_delta
citation
completed
error
```

## Agent 搜索

`POST /knowledge/search` 请求：

```json
{
  "query": "RAG 为什么需要 Reranker？",
  "top_k": 5
}
```

响应：

```json
{
  "query": "RAG 为什么需要 Reranker？",
  "results": [
    {
      "document_id": "uuid",
      "content": "相关原文",
      "score": 0.92,
      "metadata": {
        "filename": "RAG实践指南.pdf",
        "page": 32,
        "chunk_id": "uuid"
      }
    }
  ]
}
```
