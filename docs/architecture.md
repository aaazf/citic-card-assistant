# 架构基线

## 产品原则

- 用户直接提问，默认搜索全部个人知识库。
- 检索结果决定 `Knowledge`、`Hybrid` 或 `General` 回答模式。
- 没有匹配的个人知识时，使用通用 LLM 正常回答并标明来源类型。
- 前端不得直接访问 Chroma；调用链始终为 Frontend → FastAPI → Service → RAG → Vector DB。
- 用户聊天 API 与 Agent 检索 API 分离。
- 第一版保持单体模块化，不引入 Redis、Kafka、Celery、Kubernetes 或微服务。

## 分层

```text
React Frontend
    |
HTTP / SSE
    |
FastAPI API Router
    |
Service
    |
Repository / RAG
    |
SQLite + ChromaDB + Local Files
```

## 数据职责

- SQLite：知识库、文档元数据、会话、消息、模型配置、系统配置。
- ChromaDB：Chunk、Embedding、检索元数据与向量索引。
- 文件系统：上传源文件、Chroma 持久化、SQLite 数据库文件。
- Chroma 中的 Chunk 是检索事实来源；SQLite 仅保存文档级 `chunk_count`，不重复保存 Chunk 正文。

## 代码约束

- API 路由不承载业务逻辑。
- Provider 通过统一接口接入，不在业务代码中写死厂商。
- Chat 依赖 RAG 抽象；Agent API 复用 RAG，不调用 Chat。
- 关键步骤记录 query、retrieval count、score、route、model、latency、error。
- MCP 仅保留 Adapter 边界，Phase 8 再实现。
