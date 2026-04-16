"""Debug RAG retrieval for Java resume"""
from pathlib import Path
from core.enhanced_rag_retriever import EnhancedRAGRetriever

resume_text = """
基本信息
姓名：张伟
求职意向：资深Java开发工程师
个人总结
拥有6年互联网后端开发经验，精通高并发、高可用系统架构设计。擅长JVM调优及MySQL分库分表方案落地。
工作经历
北京极速云图科技有限公司 | 高级后端开发工程师 | 2021.03 - 至今
负责核心交易系统的重构与迭代，主导了从单体架构向微服务架构的迁移
带领5人小组完成了"双11"大促活动的流量承载优化，系统吞吐量提升40%
项目经验
分布式电商交易平台重构
技术栈：Java, Spring Cloud, Redis, RocketMQ, MySQL, Docker
企业级SaaS数据可视化平台
技术栈：Java, MyBatis Plus, Elasticsearch
技能清单
编程语言：精通Java，熟悉Python、Go
框架组件：熟练掌握Spring Boot, Spring Cloud, Dubbo
数据库：精通MySQL，熟练使用Redis集群
中间件：熟悉Kafka, RocketMQ消息队列
"""

retriever = EnhancedRAGRetriever(
    excel_path=Path("data/20260226105856_457.xls"),
    personas_path=Path("data/standard_job_personas_upgraded.json")
)

# Test RAG matching
results = retriever.match_resume_to_jobs(resume_text, top_k=20)

print(f"\n📊 RAG 返回 {len(results)} 个结果:")
for i, r in enumerate(results):
    print(f"{i+1}. {r['job_name']} - {r['company']} (相似度: {r['similarity']:.4f}, 来源: {r['source']})")
