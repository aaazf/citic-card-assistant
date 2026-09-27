# 阶段状态

## 基础框架：已完成

- 前后端目录、统一配置和本地数据目录
- SQLite 数据模型：知识库、文档、会话、消息、模型配置、系统配置
- API 契约与 OpenAPI 基线
- 服务、Repository、RAG、Provider 边界
- 基础测试、Ruff 与前端构建

验收：后端 48 个测试通过，前端 8 个测试通过，生产构建通过，真实 Uvicorn 联调通过。

## Phase 1：已完成

- AI 对话、知识库、最近会话、设置基础页面
- 知识库创建、列表、删除
- LLM、Embedding、检索设置读写
- 模型连接状态 API
- 最近会话仅保留页面入口，持久化按 ADR-005 留到 Phase 7

验收：健康检查、设置读取、知识库创建、列表和删除已通过真实 HTTP 验证。

## Phase 2：已完成

- PDF、TXT、Markdown 文件上传与本地存储
- 文本解析、清洗和 Chunk 切分
- OpenAI-compatible Embedding Provider
- Chroma 持久化、向量查询和文档级删除
- Document 状态流转：pending、processing、ready、failed
- 上传与删除页面操作

验收：真实 Chroma 写入、查询、删除测试通过；上传到知识库的 TXT/Markdown 处理链路通过；知识库删除会级联清理文档和向量。

## Phase 3：已完成

- 问题 Embedding 与 Chroma Top K 检索
- LLM Provider 抽象及 OpenAI-compatible 实现
- `POST /api/v1/chat` 基础回答接口
- Knowledge 模式与无知识时的基础 General 降级
- 基础引用信息返回
- 聊天输入、回答展示和错误状态

验收：有知识检索、无知识降级、LLM 未配置错误处理均通过测试；真实 Uvicorn 启动和 503 行为通过。

## Phase 4：已完成

- `RelevanceRouter` 根据检索得分和 `similarity_threshold` 自动路由
- Knowledge：高分个人知识回答
- Hybrid：部分相关时结合个人知识和通用知识，并区分来源
- General：低相关或无结果时正常使用通用知识回答
- 阈值修改后立即影响后续聊天请求
- 路由和筛选后的引用随响应返回
- 强相关阈值 0.5，部分相关阈值 0.25
- LLM Reranker 对候选 Chunk 重新打分并替换排序分数
- 向量检索与精确关键词检索混合，618 等短关键词不会因向量分数偏低被遗漏
- Reranker 异常时自动回退原始向量排序

验收：三种路由分支和动态阈值测试通过。

## Phase 5：已完成

- `POST /api/v1/chat` 支持 `Accept: text/event-stream`
- SSE 状态：understanding、searching、found、evaluating、generating、completed
- 回答通过 `answer_delta` 事件流式输出
- 引用通过 `citation` 事件返回
- 前端使用 `fetch()` 读取 POST SSE 流，不使用原生 EventSource
- 原有 JSON 聊天请求保持兼容

验收：SSE 事件顺序、流式拼接、引用事件和未配置 LLM 的预检行为均通过测试。

## Phase 6：已完成

- LLM 提示词要求使用 [1]、[2] 形式标注个人知识引用
- SSE 和 JSON 响应均包含结构化引用信息
- 新增 `GET /documents/{document_id}/chunks/{chunk_id}` 按需读取原文
- 前端可点击回答中的引用标记
- 默认关闭的右侧引用面板显示文件名、页码、相似度和原文
- 引用列表可直接打开原文

验收：Chunk 原文查询、缺失 404、引用事件和面板交互均通过测试。

## Phase 7：已完成

- Conversation 和 Message 持久化
- 首条用户消息自动生成会话标题
- 会话列表按更新时间排序
- 会话详情恢复完整消息和引用
- 继续对话时自动携带历史上下文
- JSON 和 SSE 两种聊天路径均保存完整回答
- 会话删除

验收：会话创建、列表、详情、上下文恢复、SSE 持久化、删除和缺失会话 404 均通过测试。

## Phase 8：已完成

- `POST /api/v1/knowledge/search` 结构化知识检索
- Agent API 复用 Embedding 与 Chroma 检索层
- Agent API 不调用 Chat，也不创建会话消息
- 不依赖 LLM 即可返回结构化知识
- `KnowledgeMCPAdapter` 预留 MCP 工具边界
- 未配置 Embedding 时返回 HTTP 503

验收：结构化结果、无 LLM 调用、Embedding 未配置和 MCP Adapter 复用均通过测试。

## Phase 9：已完成

- 响应式页面布局和移动端侧栏抽屉
- 桌面侧栏展开/收起及 Ctrl/Cmd+B 快捷键
- 聊天输入区 Ctrl/Cmd+K 聚焦、Enter 发送、Shift+Enter 换行
- 引用面板移动端遮罩与适配
- 知识库拖拽上传
- RAG 高级检索参数默认折叠
- Loading、空状态和错误提示完善
- 淡入、上滑动画和 `prefers-reduced-motion` 支持
- 聊天消息自动滚动

验收：前端 6 个测试全部通过，TypeScript 检查和生产构建通过。

## 知识库体验增强

- 左侧优先展示已有知识库和搜索
- “新建知识库”改为弹窗
- 当前知识库显示资料数、知识片段数和真实索引状态
- 添加资料区域压缩到约 132px
- 文档状态显示真实处理状态
- 文档卡片支持打开右侧详情抽屉
- 支持 PDF 内嵌预览、纯文本原文预览和 Chunk 列表查看
- 不伪造解析、Embedding 或索引进度

## 首次欢迎页

- 首次打开知识库显示小智欢迎页
- 支持直接提问并自动进入主聊天
- 点击“进入知识库”后记住状态，后续直接进入列表
- 设置页可重新查看功能介绍

## 文件格式扩展

- DOCX 解析正文和表格文本
- EPUB 按 spine 阅读顺序解析章节正文，并保留章节标题元数据
- PNG、JPG、JPEG、WEBP、BMP、TIFF 图片使用本地 RapidOCR 提取文字
- 图片 OCR 结果进入原有 Chunk、Embedding 和 Chroma 流程
- Embedding 请求按批次提交，避免长篇资料超过模型单次输入限制
- 索引按 Embedding 模型和向量维度版本化，重建时保留旧索引并支持切换回滚
- PDF、TXT、Markdown 原有行为保持不变
- 修复上传文件 UUID 生成顺序，避免不同文件覆盖为 None.pdf

## 定向知识库问答

- 知识库顶部增加“问答”入口
- 点击后返回主聊天界面，不复制第二套聊天组件
- `knowledge_base_id` 限制向量、关键词和 Reranker 的检索范围
- 默认严格使用当前知识库，不自动混入通用回答
- 可主动勾选“允许通用补充”
- 会话记录保存知识库范围
- 过往对话显示“知识库问答”标签并恢复范围

## 网站入口动态体验

- 首次访问网站显示引导页并永久记录已访问
- 引导页支持直接提问和进入知识库
- 新增渐变光晕、悬浮卡片、分层进入和按钮光泽
- 聊天流式回答增加动态光标
- 连接状态增加轻量呼吸效果
- 遵循 `prefers-reduced-motion`

## 检索与空白修复

- 单字符、纯数字 1–2 位、问号和常见寒暄不触发知识库检索
- 618、AI 等有效关键词仍正常执行混合检索
- 流式回答失败时在气泡内显示原因和重试按钮
- 刷新后如果最后一条没有回答，自动补上未完成提示
- 恢复历史时忽略空助手消息
- 连续重复的失败用户重试消息在展示时折叠

## 全部阶段完成
