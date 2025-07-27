# EchoIntellect

📦 本工具为纯本地运行的个人知识库助手
🎓 仅供学习研究使用，生产环境慎用哦～

# 目录结构

```
echo-intellect/
├── app/
│   ├── main.py                 # 应用入口点
│   ├── api/
│   │   └── routes.py           # API路由定义
│   ├── chains/
│   │   ├── query_processing_chain.py  # 查询处理链
│   │   └── retrieval_chain.py  # 检索链
│   ├── components/
│   │   ├── query_transformation/
│   │   │   ├── query_optimizer.py  # 指代消除、上下文补全
│   │   │   └── query_expander.py   # 查询扩展
│   │   ├── retrievers/
│   │   │   ├── hybrid_retriever.py # 结合embedding和BM25
│   │   │   └── parallel_retriever.py # 并行检索
│   │   ├── mergers/
│   │   │   └── rrf_merger.py   # 实现RRF算法合并检索结果
│   │   ├── rerankers/
│   │   │   └── custom_reranker.py  # 结果重排组件
│   │   └── filters/
│   │       └── token_relevance_filter.py # 结果过滤组件
│   ├── document_loaders/
│   │   └── custom_loaders.py   # 文档加载器
│   ├── embeddings/
│   │   └── embedding_models.py # 向量嵌入模型
│   ├── memory/
│   │   └── conversation_memory.py  # 对话历史记忆组件
│   ├── vectorstores/
│   │   ├── postgres_vector.py  # PostgreSQL+PGVector适配器
│   │   └── mongo_metadata.py   # MongoDB元数据存储
│   ├── models/
│   │   └── data_models.py      # 数据模型定义
│   ├── prompts/
│   │   └── rag_prompts.py      # RAG提示模板
│   └── utils/
│       └── langchain_utils.py  # 工具函数
├── config/
│   └── settings.py             # 配置文件
├── deploy/
│   ├── docker-compose.yaml     # Docker容器编排配置
│   ├── Dockerfile              # Docker镜像构建文件
│   └── nginx.conf              # Nginx配置文件
├── tests/
│   └── test_chains.py          # 测试示例
├── dev.md                      # 开发文档
├── pyproject.toml              # Python项目配置文件
├── Makefile                    # 构建和部署脚本
├── LICENSE                     # 许可证文件
└── README.md                   # 项目说明文档
```
