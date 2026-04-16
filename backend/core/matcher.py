
import json
import sys
import re
from pathlib import Path
from collections import Counter
import pandas as pd
# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.soft_skill_evaluator import evaluate_soft_skills


def extract_education_from_text(text: str) -> str:
    """
    从岗位详情文本中提取学历要求
    返回：'博士', '硕士', '本科', '大专', 或 '不限'
    """
    if not text or pd.isna(text):
        return '不限'
    
    text = str(text)
    
    # 学历关键词映射（优先级从高到低）
    edu_patterns = [
        (r'博士', '博士'),
        (r'硕士', '硕士'),
        (r'本科', '本科'),
        (r'大专', '大专'),
        (r'专科', '大专'),
    ]
    
    # 查找最高学历要求
    for pattern, edu_level in edu_patterns:
        if re.search(pattern, text):
            return edu_level
    
    # 如果没有明确提到，检查是否有"不限"或"无要求"
    if re.search(r'不限|无要求|无限制', text):
        return '不限'
    
    return '不限'  # 默认


def extract_experience_from_text(text: str) -> str:
    """
    从岗位详情文本中提取经验要求
    返回：'10 年以上', '5-10 年', '3-5 年', '1-3 年', '应届毕业生', 或 '不限'
    """
    if not text or pd.isna(text):
        return '不限'
    
    text = str(text)
    
    # 应届毕业生
    if re.search(r'应届|在校生|实习生', text):
        return '应届毕业生'
    
    # 经验年限模式匹配
    # 匹配：3-5 年、3 年以上、5 年经验等
    year_patterns = [
        (r'(\d+)[-~至](\d+)\s*年', lambda m: f"{m.group(1)}-{m.group(2)}年"),
        (r'(\d+)\s*年以上', lambda m: f"{m.group(1)}年以上"),
        (r'(\d+)\s*年经验', lambda m: f"{m.group(1)}年"),
        (r'至少\s*(\d+)\s*年', lambda m: f"{m.group(1)}年以上"),
    ]
    
    for pattern, formatter in year_patterns:
        match = re.search(pattern, text)
        if match:
            if callable(formatter):
                return formatter(match)
            return formatter
    
    # 检查是否有"不限"或"无要求"
    if re.search(r'不限|无要求|无经验要求', text):
        return '不限'
    
    return '不限'  # 默认


class MatchEngine:
    #personas_path:岗位画像文件路径, excel_path:真实招聘数据文件路径,user_rag:是否使用增强版RAG检索
    def __init__(self, personas_path=None, excel_path=None, use_rag=True):
        if personas_path is None:
            personas_path = Path(__file__).parent.parent / "data" / "standard_job_personas_upgraded.json"
        with open(personas_path, 'r', encoding='utf-8') as f:
            self.personas = json.load(f)

        # 技能等级分值映射
        self.level_map = {"了解": 0.6, "熟悉": 0.8, "精通": 1.0}
        
        # 缓存软素质评估结果，避免重复调用大模型
        self._soft_skill_cache = {}
        
        # 加载 Excel 统计数据
        self.excel_stats = {}
        self.df = None  # 保存原始 DataFrame，供外部使用
        if excel_path:
            import pandas as pd
            self.df = pd.read_excel(excel_path)  # 保存为实例属性
            for job_name in self.personas.keys():
                job_data = self.df[self.df['岗位名称'] == job_name]
                if len(job_data) > 0:
                    # 解析薪资范围（简化处理）
                    avg_salary = 0
                    try:
                        salary_str = str(job_data['薪资范围'].iloc[0]) if '薪资范围' in job_data.columns else ''
                        if '-' in salary_str and '元' in salary_str:
                            parts = salary_str.replace('元', '').replace('万', '0000').replace('k', '000').split('-')
                            if len(parts) == 2:
                                low = float(parts[0].strip())
                                high = float(parts[1].strip())
                                avg_salary = (low + high) / 2
                    except:
                        pass
                    
                    # 使用 NLP 从岗位详情中提取学历和经验要求
                    education_list = []
                    experience_list = []
                    
                    # 确定岗位详情列名（支持多种可能的列名）
                    detail_col = None
                    for col_name in ['岗位详情', '岗位描述', '职位描述', '工作内容', 'details']:
                        if col_name in job_data.columns:
                            detail_col = col_name
                            break
                    
                    # 从每条记录中提取信息
                    if detail_col:
                        for _, row in job_data.iterrows():
                            detail_text = str(row.get(detail_col, ''))
                            edu = extract_education_from_text(detail_text)
                            exp = extract_experience_from_text(detail_text)
                            education_list.append(edu)
                            experience_list.append(exp)
                    
                    self.excel_stats[job_name] = {
                        'avg_salary': avg_salary,
                        'hire_count': len(job_data),
                        'education_dist': Counter(education_list) if education_list else {},
                        'experience_dist': Counter(experience_list) if experience_list else {}
                    }
        
        # 初始化 RAG 检索器（增强版）
        self.rag_retriever = None
        if use_rag and excel_path:
            try:
                from core.enhanced_rag_retriever import get_enhanced_retriever
                personas_file_path = Path(__file__).parent.parent / "data" / "standard_job_personas_upgraded.json"
                self.rag_retriever = get_enhanced_retriever(excel_path, personas_file_path)
                stats = self.rag_retriever.get_collection_stats()
                print(f"✅ 增强版 RAG 检索器已初始化")
                print(f"   - 真实招聘岗位：{stats.get('excel_jobs', 0)} 个")
                print(f"   - 标准岗位画像：{stats.get('standard_personas', 0)} 个")
            except Exception as e:
                print(f"⚠️ RAG 初始化失败：{str(e)}")

    def calculate_score(self, student_profile: dict, target_job_key: str, soft_evaluation=None):
        """
        计算学生画像与目标岗位的匹配得分
        student_profile: 经LLM解析后的学生简历数据
        target_job_key: 目标岗位名称 (如 "前端开发")
        soft_evaluation: 预计算的软素质评估结果（可选）
        """
        job = self.personas.get(target_job_key)
        if not job:
            return None

        # --- 维度 1: 专业技能 (40分) ---
        skill_score = 0
        job_skills = job.get("专业技能", [])
        student_skills = student_profile.get("skills", {})  # 格式: {"Java": "精通", "MySQL": "熟悉"}

        for s_req in job_skills:
            name = s_req['name']
            req_level = s_req['level']
            weight = s_req.get('weight', 0.1)

            # 找到学生对应的技能
            if name in student_skills:
                s_level = student_skills[name]
                # 计算得分：(学生等级分 / 要求等级分) * 权重 * 40
                # 如果学生等级更高，最高给满分
                ratio = min(1.0, self.level_map.get(s_level, 0.5) / self.level_map.get(req_level, 0.8))
                skill_score += ratio * weight * 40

        # --- 维度 2: 硬性门槛 (20分) ---
        hard_score = 20  # 默认满分，除非明确不符
        edu_req = job.get("教育要求", "不限")
        student_edu = student_profile.get("education", "")
        
        if edu_req and edu_req != "不限" and student_edu:
            # 学历降级兼容逻辑
            edu_levels = {"大专": 1, "本科": 2, "硕士": 3, "博士": 4}
            
            # 岗位要求可能包含多个值，如 "大专,本科" 或 "本科及以上"
            req_min_level = 999
            for edu_key, edu_val in edu_levels.items():
                if edu_key in edu_req:
                    req_min_level = min(req_min_level, edu_val)
            
            # 学生学历等级
            stu_level = 0
            for edu_key, edu_val in edu_levels.items():
                if edu_key in student_edu:
                    stu_level = max(stu_level, edu_val)
            
            if req_min_level == 999:
                # 岗位要求无法识别，默认满分
                hard_score = 20
            elif stu_level >= req_min_level:
                hard_score = 20
            elif stu_level == req_min_level - 1:
                hard_score = 15  # 略低但可接受
            else:
                hard_score = 10

        # --- 维度 3: 软性素质 (20 分) ---
        soft_score = 16  # 默认基础分
        if soft_evaluation:
            # 使用预计算的评估结果
            dimensions = ['communication', 'learning', 'pressure_tolerance', 
                         'innovation', 'teamwork', 'responsibility']
            valid_scores = []
            for dim in dimensions:
                ev = soft_evaluation.get(dim, {})
                score = ev.get('score')
                evidence = ev.get('evidence', '')
                if score and len(evidence) > 5:
                    valid_scores.append(score)
            
            if valid_scores:
                avg_score = sum(valid_scores) / len(valid_scores)
                soft_score = int(avg_score * 0.2)

        # --- 维度 4: 项目对标 (20分) ---
        # 基于简历中项目的实际量化成果评分
        project_score = 15  # 默认基础分
        projects = student_profile.get("projects", [])
        if projects:
            bonus = 0
            for proj in projects:
                proj_desc = proj.get("description", "") + proj.get("responsibility", "")
                # 有量化成果加分
                import re
                if re.search(r'\d+%|提升|降低|优化|从.*到|\d+ms|\d+QPS', proj_desc):
                    bonus += 1.5  # 每个有量化成果的项目加分
                # 有明确技术栈加分
                if proj.get("tech_stack"):
                    bonus += 0.5
            project_score = min(20, 12 + bonus)

        total_score = skill_score + hard_score + soft_score + project_score

        return {
            "total_score": round(total_score, 1),
            "details": {
                "professional": round(skill_score, 1),
                "hard_req": hard_score,
                "soft_skills": soft_score,
                "project_exp": project_score
            }
        }
    
    def recommend_jobs(self, student_profile: dict, top_n: int = 5, use_rag=True):
        """
        根据学生画像推荐匹配的岗位及具体公司
        student_profile: 经 LLM 解析后的学生简历数据
        top_n: 推荐岗位数量
        use_rag: 是否使用 RAG 增强
        """
        # 预先评估软素质（只调用一次大模型）
        soft_evaluation = None
        if student_profile.get("resume_text"):
            resume_text = student_profile["resume_text"]
            if resume_text not in self._soft_skill_cache:
                try:
                    self._soft_skill_cache[resume_text] = evaluate_soft_skills(resume_text)
                except Exception as e:
                    print(f"⚠️ 软素质评估失败，使用默认值：{str(e)}")
                    self._soft_skill_cache[resume_text] = {}
            soft_evaluation = self._soft_skill_cache[resume_text]
        
        recommendations = []
        
        # 第一步: 规则匹配推荐（只从标准岗位画像中推荐）
        for job_name in self.personas.keys():
            score_result = self.calculate_score(student_profile, job_name, soft_evaluation=soft_evaluation)
            if score_result:
                recommendations.append({
                    "job_name": job_name,
                    "total_score": score_result["total_score"],
                    "details": score_result["details"],
                    "job_requirements": self.personas[job_name],
                    "excel_stats": self.excel_stats.get(job_name, {}),
                    "source": "rule_based",
                    "recommended_positions": []  # 新增：用于存放具体公司推荐
                })
        
        # 方法 2: RAG 语义检索（用于增强排序 + 提取具体公司）
        rag_results = []
        if use_rag and self.rag_retriever and student_profile.get('resume_text'):
            try:
                print(f"🔍 使用 RAG 增强岗位排序并提取具体职位...")
                rag_results = self.rag_retriever.match_resume_to_jobs(
                    student_profile['resume_text'],
                    top_k=top_n * 5,
                    use_personas=True
                )
                
                print(f"📊 RAG 返回了 {len(rag_results)} 条匹配结果")
                
                # 建立岗位名到 RAG 详情的映射
                rag_by_job = {}
                for r in rag_results:
                    jn = r.get('job_name', '')
                    if jn not in rag_by_job:
                        rag_by_job[jn] = []
                    rag_by_job[jn].append(r)
                
                print(f"📊 RAG 覆盖了 {len(rag_by_job)} 个岗位")
                
                # 为规则推荐中的岗位添加 RAG 分数和具体公司
                for rec in recommendations:
                    jn = rec['job_name']
                    
                    # 精确匹配
                    if jn in rag_by_job:
                        best_rag = max(rag_by_job[jn], key=lambda x: x.get('similarity', 0))
                        rec['rag_similarity'] = best_rag['similarity']
                        rec['total_score'] = rec['total_score'] * 0.6 + best_rag['similarity'] * 100 * 0.4
                        
                        # 只使用有company字段的RAG结果（排除standard_persona源）
                        valid_rag_results = [r for r in rag_by_job[jn] if r.get('company', '').strip()]
                        if valid_rag_results:
                            rec['recommended_positions'] = [
                                {
                                    'company': r.get('company', '未知公司'),
                                    'salary': r.get('salary', '面议'),
                                    'similarity': round(r.get('similarity', 0) * 100, 1)
                                }
                                for r in valid_rag_results[:3]
                            ]
                            print(f"   ✅ 岗位 [{jn}] 精确匹配到 {len(rec['recommended_positions'])} 个公司")
                        else:
                            print(f"   ⚠️ 岗位 [{jn}] RAG结果中无公司数据，将走兜底逻辑")
                    else:
                        # 模糊匹配：尝试匹配包含关系
                        matched_rag_results = []
                        for rag_jn, rag_list in rag_by_job.items():
                            if jn in rag_jn or rag_jn in jn:
                                matched_rag_results.extend(rag_list)
                        
                        if matched_rag_results:
                            # 只使用有company字段的结果
                            valid_matched = [r for r in matched_rag_results if r.get('company', '').strip()]
                            if valid_matched:
                                # 按相似度排序，取前3
                                valid_matched.sort(key=lambda x: x.get('similarity', 0), reverse=True)
                                best_rag = valid_matched[0]
                                rec['rag_similarity'] = best_rag['similarity']
                                rec['total_score'] = rec['total_score'] * 0.6 + best_rag['similarity'] * 100 * 0.4
                                
                                rec['recommended_positions'] = [
                                    {
                                        'company': r.get('company', '未知公司'),
                                        'salary': r.get('salary', '面议'),
                                        'similarity': round(r.get('similarity', 0) * 100, 1)
                                    }
                                    for r in valid_matched[:3]
                                ]
                                print(f"   ✅ 岗位 [{jn}] 模糊匹配到 {len(rec['recommended_positions'])} 个公司")
                            else:
                                print(f"   ⚠️ 岗位 [{jn}] 模糊匹配结果中无公司数据，将走兜底逻辑")
                        else:
                            print(f"   ⚠️ 岗位 [{jn}] 在 RAG 结果中未找到（共 {len(rag_by_job)} 个岗位）")
            except Exception as e:
                print(f"⚠️ RAG 增强失败：{str(e)}")
                import traceback
                traceback.print_exc()
        
        # 兜底方案：如果 RAG 没有返回数据，从 Excel 数据中提取真实公司推荐
        for rec in recommendations:
            if not rec.get('recommended_positions') or len(rec['recommended_positions']) == 0:
                job_name = rec['job_name']
                
                # 优先尝试从 Excel 中提取真实公司数据
                if self.df is not None and len(self.df) > 0:
                    # 精确匹配 + 模糊匹配（使用 regex=False 避免正则表达式错误）
                    matched_jobs = self.df[self.df['岗位名称'].str.contains(job_name, na=False, case=False, regex=False)]
                    
                    # 如果精确匹配不到，尝试反向包含（如"Java"匹配"Java开发工程师"）
                    if len(matched_jobs) == 0:
                        # 提取关键词进行模糊匹配
                        keywords = [job_name] if len(job_name) <= 4 else [job_name[:4], job_name[2:]]
                        for kw in keywords:
                            if len(kw) >= 2:
                                matched_jobs = self.df[self.df['岗位名称'].str.contains(kw, na=False, case=False, regex=False)]
                                if len(matched_jobs) > 0:
                                    break
                    
                    if len(matched_jobs) > 0:
                        # 随机选取3个不同的公司
                        sampled = matched_jobs.sample(min(3, len(matched_jobs)))
                        rec['recommended_positions'] = []
                        for _, row in sampled.iterrows():
                            rec['recommended_positions'].append({
                                'company': str(row.get('公司名称', row.get('company', '未知公司'))),
                                'salary': str(row.get('薪资范围', row.get('salary', '面议'))),
                                'similarity': round(rec['total_score'] * 0.95, 1)
                            })
                        print(f"   ✅ 从 Excel 提取到 {len(rec['recommended_positions'])} 个真实公司推荐：{job_name}")
                        for pos in rec['recommended_positions']:
                            print(f"      - {pos['company']} | {pos['salary']}")
                    else:
                        # 完全没有匹配数据，使用兜底模拟数据
                        excel_stats = rec.get('excel_stats', {})
                        avg_salary = excel_stats.get('avg_salary', 0)
                        
                        if avg_salary > 0:
                            salary_text = f"{avg_salary/1000:.0f}k-{int(avg_salary*1.5/1000)}k"
                        else:
                            salary_text = "面议"
                        
                        base_similarity = rec['total_score']
                        rec['recommended_positions'] = [
                            {
                                'company': f"某知名{job_name}企业",
                                'salary': salary_text,
                                'similarity': round(base_similarity * 0.95, 1)
                            },
                            {
                                'company': f"某{job_name}科技公司",
                                'salary': salary_text,
                                'similarity': round(base_similarity * 0.9, 1)
                            },
                            {
                                'company': f"某互联网{job_name}公司",
                                'salary': salary_text,
                                'similarity': round(base_similarity * 0.85, 1)
                            }
                        ]
                        print(f"   💼 为岗位 [{job_name}] 生成兜底公司推荐")
        
        # 按综合分数排序，返回 top_n（只返回匹配度>60的岗位）
        recommendations = [r for r in recommendations if r["total_score"] >= 60.0]
        recommendations.sort(key=lambda x: x["total_score"], reverse=True)
        return recommendations[:top_n]