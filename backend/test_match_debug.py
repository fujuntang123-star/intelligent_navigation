 """测试匹配流程，检查为什么出现"暂无具体职位数据" """
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.matcher import MatchEngine
import json

# 初始化匹配引擎
excel_path = Path(__file__).parent / "data" / "20260226105856_457.xls"
print("🔧 初始化匹配引擎...")
engine = MatchEngine(excel_path=excel_path, use_rag=True)

# 模拟一份简历数据
test_profile = {
    "hard_thresholds": {
        "education": "本科",
        "major": "计算机科学",
        "certificates": []
    },
    "professional_skills": [
        {"name": "Python", "level": 4, "level_text": "精通"},
        {"name": "MySQL", "level": 3, "level_text": "熟悉"},
        {"name": "Django", "level": 3, "level_text": "熟悉"}
    ],
    "soft_skills": [],
    "projects": [
        {
            "title": "Web应用开发",
            "description": "使用Django开发了一个电商网站，提升了30%的订单转化率",
            "responsibility": "负责后端开发",
            "tech_stack": "Python, Django, MySQL, Redis"
        }
    ],
    "skills": {"Python": "精通", "MySQL": "熟悉", "Django": "熟悉"},
    "education": "本科",
    "resume_text": "熟练使用Python和Django进行后端开发，熟悉MySQL数据库"
}

print("\n🎯 测试岗位推荐...")
recommendations = engine.recommend_jobs(test_profile, top_n=5, use_rag=True)

print(f"\n📊 推荐结果数量: {len(recommendations)}")
if recommendations:
    for i, rec in enumerate(recommendations):
        print(f"\n【岗位 {i+1}】 {rec['job_name']}")
        print(f"  总分: {rec['total_score']}")
        print(f"  来源: {rec.get('source', 'unknown')}")
        print(f"  推荐公司数: {len(rec.get('recommended_positions', []))}")
        
        if rec.get('recommended_positions'):
            print(f"  推荐公司详情:")
            for pos in rec['recommended_positions']:
                print(f"    - {pos['company']} | {pos['salary']} | 匹配度 {pos['similarity']}%")
        else:
            print("  ⚠️ 没有推荐公司！")
else:
    print("❌ 没有任何推荐！")

# 单独检查兜底逻辑
print("\n\n🔍 单独检查兜底逻辑...")
print(f"  excel_stats 中的岗位数: {len(engine.excel_stats)}")
for job_name, stats in list(engine.excel_stats.items())[:3]:
    print(f"  岗位 '{job_name}': avg_salary={stats.get('avg_salary', 0)}, hire_count={stats.get('hire_count', 0)}")

# 单独检查 TF-IDF 检索
print("\n\n🔍 单独检查 TF-IDF 检索...")
from core.enhanced_rag_retriever import get_enhanced_retriever
from pathlib import Path
personas_file_path = Path(__file__).parent / "data" / "standard_job_personas_upgraded.json"
retriever = get_enhanced_retriever(excel_path, personas_file_path)

print(f"  使用 TF-IDF 模式: {retriever.use_tfidf}")
print(f"  tfidf_job_documents 数量: {len(retriever.tfidf_job_documents)}")
print(f"  tfidf_persona_documents 数量: {len(retriever.tfidf_persona_documents)}")

# 测试 TF-IDF 相似度计算
resume_text = test_profile['resume_text']
resume_vec = retriever.tfidf_vectorizer.transform([resume_text])
job_vecs = retriever.tfidf_vectorizer.transform(retriever.tfidf_job_documents)
from sklearn.metrics.pairwise import cosine_similarity
job_similarities = cosine_similarity(resume_vec, job_vecs).flatten()

print(f"  TF-IDF 检索结果:")
print(f"    最高相似度: {max(job_similarities):.6f}")
print(f"    平均相似度: {sum(job_similarities)/len(job_similarities):.6f}")

# 检查有多少超过阈值 0.05
above_05 = sum(1 for s in job_similarities if s > 0.05)
above_01 = sum(1 for s in job_similarities if s > 0.01)
above_001 = sum(1 for s in job_similarities if s > 0.001)
print(f"    > 0.05 的数量: {above_05}")
print(f"    > 0.01 的数量: {above_01}")
print(f"    > 0.001 的数量: {above_001}")

# 显示前 10 个最高相似度
import numpy as np
top_indices = np.argsort(job_similarities)[::-1][:10]
print(f"    前 10 个最高相似度:")
for idx in top_indices:
    meta = retriever.tfidf_job_metadatas[idx]
    print(f"      {meta['job_name']} - {meta['company']}: {job_similarities[idx]:.6f}")
