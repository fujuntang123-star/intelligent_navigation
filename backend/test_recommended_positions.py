import asyncio
import json
from pathlib import Path
from core.matcher import MatchEngine

excel_path = Path('D:/contest/backend/data/20260226105856_457.xls')
engine = MatchEngine(excel_path=excel_path, use_rag=True)

# 模拟学生画像
test_profile = {
    'professional_skills': [
        {'name': 'Java', 'level_text': '精通'},
        {'name': 'MySQL', 'level_text': '熟悉'},
        {'name': 'Spring Boot', 'level_text': '熟悉'},
        {'name': 'Python', 'level_text': '熟悉'}
    ],
    'education': '本科',
    'experience': '应届毕业生',
    'projects': [
        {
            'title': '电商系统',
            'description': '基于Spring Boot开发的电商平台，使用MySQL数据库，实现了订单管理、库存管理等功能。提升了系统性能30%',
            'tech_stack': 'Java, Spring Boot, MySQL, Redis'
        }
    ]
}

# 格式化技能
formatted_skills = {s['name']: s.get('level_text', '熟悉') for s in test_profile.get('professional_skills', [])}
test_profile['skills'] = formatted_skills

print('🎯 测试岗位推荐...')
recommendations = engine.recommend_jobs(test_profile, top_n=5, use_rag=True)

print(f'\n📊 推荐结果数量: {len(recommendations)}')
if recommendations:
    for i, rec in enumerate(recommendations):
        print(f'\n【岗位 {i+1}】 {rec["job_name"]}')
        print(f'  总分: {rec["total_score"]}')
        print(f'  推荐公司数: {len(rec.get("recommended_positions", []))}')
        
        if rec.get('recommended_positions'):
            print(f'  推荐公司详情:')
            for pos in rec['recommended_positions']:
                print(f'    - {pos["company"]} | {pos["salary"]} | 匹配度 {pos["similarity"]}%')
        else:
            print('  ⚠️ 没有推荐公司！')
else:
    print('❌ 没有任何推荐！')
