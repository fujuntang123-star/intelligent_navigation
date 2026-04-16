from neo4j import GraphDatabase
import json
from pathlib import Path
import pandas as pd


class CareerGraph:
    def __init__(self, uri, user, password):
        try:
            print(f"🔌 正在连接 Neo4j: {uri}")
            self.driver = GraphDatabase.driver(
                uri,
                auth=(user, password),
                connection_timeout=5,  # 5秒连接超时
                max_connection_lifetime=3600
            )
            # 测试连接
            self.driver.verify_connectivity()
            print("✅ Neo4j 连接成功")
        except Exception as e:
            print(f"⚠️ Neo4j 连接失败: {str(e)}")
            print("📝 将使用空图谱模式运行（部分功能将受限）")
            self.driver = None

    def close(self):
        self.driver.close()

    def import_data(self, json_path, excel_path=None):
        """将升级后的 JSON 画像导入图数据库
        
        Args:
            json_path: 岗位画像 JSON 文件路径
            excel_path: Excel 源数据文件路径（可选，用于提取市场数据）
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 如果提供了 Excel 路径，加载市场数据
        market_data = {}
        if excel_path and Path(excel_path).exists():
            print(f"📊 正在从 Excel 提取市场数据...")
            df = pd.read_excel(excel_path)
            
            for job_name in data.keys():
                # 筛选该岗位的所有记录
                job_rows = df[df['岗位名称'] == job_name]
                
                if len(job_rows) > 0:
                    # 计算平均招聘次数
                    hire_count = len(job_rows)
                    
                    # 提取薪资范围（取第一条记录）
                    salary_range = job_rows.iloc[0].get('薪资范围', '')
                    
                    # 从岗位详情中提取学历要求（取最高要求）
                    edu_priority = {
                        '大专': 1,
                        '专科': 1,
                        '本科': 2,
                        '硕士': 3,
                        '博士': 4
                    }
                    
                    edu_req = "不限"
                    max_priority = 0
                    
                    for _, row in job_rows.iterrows():
                        detail = str(row.get('岗位详情', ''))
                        
                        # 检查每条记录中的学历要求，保留最高级别
                        if '博士' in detail:
                            edu_req = '博士'
                            max_priority = edu_priority['博士']
                            break  # 博士是最高学历，找到即可停止
                        elif '硕士' in detail:
                            if edu_priority['硕士'] > max_priority:
                                edu_req = '硕士'
                                max_priority = edu_priority['硕士']
                        elif '本科' in detail:
                            if edu_priority['本科'] > max_priority:
                                edu_req = '本科'
                                max_priority = edu_priority['本科']
                        elif '大专' in detail or '专科' in detail:
                            if edu_priority['大专'] > max_priority:
                                edu_req = '大专'
                                max_priority = edu_priority['大专']
                    
                    market_data[job_name] = {
                        'salary_range': str(salary_range) if salary_range else None,
                        'edu_req': edu_req,
                        'hire_count': hire_count
                    }
            
            print(f"✅ 提取了 {len(market_data)} 个岗位的市场数据")
    
        with self.driver.session() as session:
            # 1. 危险操作：清空旧数据（仅限开发阶段）
            session.run("MATCH (n) DETACH DELETE n")
    
            for job_key, job_info in data.items():
                job_name = job_info.get("岗位名称", job_key)
                
                # 从 Excel 市场数据中获取，如果没有则使用默认值
                market = market_data.get(job_name, {})
                salary_range = market.get('salary_range', job_info.get("薪资范围"))
                edu_req = market.get('edu_req', job_info.get("教育要求", ""))
                hire_count = market.get('hire_count', 0)
                
                # 2. 创建/更新岗位节点（添加市场数据与行业趋势）
                session.run("""
                    MERGE (j:Job {name: $name})
                    SET j.salary_range = $salary_range,
                        j.market_salary = $market_salary,
                        j.edu_req = $edu_req,
                        j.hire_count = $hire_count,
                        j.industry_trend = $industry_trend
                """, name=job_name,
                    salary_range=salary_range,
                    market_salary=job_info.get("市场薪资", ""),
                    edu_req=edu_req,
                    hire_count=hire_count,
                    industry_trend=job_info.get("industry_trend", ""))
    
                # 3. 处理专业技能（数组结构）
                skills = job_info.get("专业技能", [])
                for s in skills:
                    skill_name = s['name']
                    level = s['level']
                    weight = s.get('weight', 0.1)
                    # 创建/更新技能节点
                    session.run("MERGE (s:Skill {name: $name})", name=skill_name)
                    # 建立“要求”关系
                    session.run("""
                        MATCH (j:Job {name: $j_name}), (s:Skill {name: $s_name})
                        MERGE (j)-[r:REQUIRES]->(s)
                        SET r.level = $level, r.weight = $weight
                    """, j_name=job_name, s_name=skill_name, level=level, weight=weight)
            
        print(f"✅ 岗位节点构建成功：已建立 {len(data)} 个岗位。")
            
        # 4. 导入垂直晋升路径
        self._import_vertical_paths()
            
        # 5. 导入换岗路径
        self._import_transfer_paths()
        
    def _import_vertical_paths(self):
        """导入垂直晋升路径"""
        try:
            # 使用绝对路径
            vertical_path = Path(__file__).parent.parent / 'data' / 'job_vertical_paths.json'
            with open(vertical_path, 'r', encoding='utf-8') as f:
                vertical_data = json.load(f)
                
            with self.driver.session() as session:
                for job_name, paths in vertical_data.items():
                    if paths.get('next_role'):
                        params = {
                            'from': job_name,
                            'to': paths['next_role'],
                            'level': paths['current_level']
                        }
                        session.run("""
                            MATCH (j1:Job {name: $from}), (j2:Job {name: $to})
                            MERGE (j1)-[r:PROMOTES_TO]->(j2)
                            SET r.level = $level, r.type = 'vertical'
                        """, **params)
                    if paths.get('previous_role'):
                        params = {
                            'from': paths['previous_role'],
                            'to': job_name,
                            'level': paths['current_level'] - 1
                        }
                        session.run("""
                            MATCH (j1:Job {name: $from}), (j2:Job {name: $to})
                            MERGE (j1)-[r:PROMOTES_TO]->(j2)
                            SET r.level = $level, r.type = 'vertical'
                        """, **params)
                
            print(f"✅ 垂直晋升路径导入成功。")
        except Exception as e:
            print(f"⚠️ 导入垂直路径失败：{str(e)}")
        
    def _import_transfer_paths(self):
        """导入换岗路径"""
        try:
            # 检查文件是否存在
            transfer_path = Path(__file__).parent.parent / 'data' / 'job_transfer_paths.json'
            if not transfer_path.exists():
                print(f"⚠️ 换岗路径文件不存在: {transfer_path}")
                print("💡 将基于技能相似度动态计算换岗路径")
                return
            
            with open(transfer_path, 'r', encoding='utf-8') as f:
                transfer_data = json.load(f)
                
            with self.driver.session() as session:
                for job_name, paths in transfer_data.items():
                    for path in paths[:3]:  # 每个岗位保留 3 条换岗路径
                        params = {
                            'from': job_name,
                            'to': path['to'],
                            'score': path['score'],
                            'reason': path['reason']
                        }
                        session.run("""
                            MATCH (j1:Job {name: $from}), (j2:Job {name: $to})
                            MERGE (j1)-[r:TRANSFERS_TO]->(j2)
                            SET r.score = $score, r.reason = $reason, r.type = 'transfer'
                        """, **params)
                
            print(f"✅ 换岗路径导入成功。")
        except Exception as e:
            print(f"⚠️ 导入换岗路径失败：{str(e)}")

    def find_transfer_paths(self, current_job_name, top_n: int = 5):
        """寻找换岗路径的核心 Cypher 查询 (基于 Jaccard 相似系数)"""
        if self.driver is None:
            print(f"⚠️ Neo4j 未连接，返回空换岗路径")
            return []
        
        query = """
        MATCH (j1:Job {name: $name})
        // 1. 获取当前岗位 j1 的总技能数 (|A|)
        WITH j1, count {(j1)-[:REQUIRES]->()} AS size_A

        // 2. 找到有交集的候选岗位 j2，并计算共同技能数 (|A ∩ B|)
        MATCH (j1)-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job)
        WHERE j1 <> j2
        WITH j1, size_A, j2, count(s) AS intersection

        // 3. 获取目标岗位 j2 的总技能数 (|B|)
        WITH j2, intersection, size_A, count {(j2)-[:REQUIRES]->()} AS size_B

        // 4. 计算并集大小 (|A ∪ B| = |A| + |B| - |A ∩ B|)
        WITH j2, intersection, size_B, (size_A + size_B - intersection) AS union_size

        // 5. 计算杰卡德相似度并返回所需字段
        RETURN j2.name AS target_job,
               round(toFloat(intersection) / union_size, 4) AS jaccard_similarity,
               size_B AS target_total_skills,
               (size_B - intersection) AS skill_gap_count
        ORDER BY jaccard_similarity DESC 
        LIMIT $top_n
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, name=current_job_name, top_n=top_n)
                return [record.data() for record in result]
        except Exception as e:
            print(f"⚠️ 查询换岗路径失败: {str(e)}")
            return []
    
    def find_vertical_paths(self, job_name):
        """查找垂直晋升路径（岗位层级关系）"""
        query = """
        MATCH (j:Job {name: $name})
        OPTIONAL MATCH (j)-[r:PROMOTES_TO]->(higher:Job)
        RETURN higher.name AS target_job, 'up' AS direction, r.level AS level
        UNION ALL
        MATCH (j:Job {name: $name})
        OPTIONAL MATCH (lower:Job)-[r:PROMOTES_TO]->(j)
        RETURN lower.name AS target_job, 'down' AS direction, r.level AS level
        """
        with self.driver.session() as session:
            result = session.run(query, name=job_name)
            return [record.data() for record in result]
    
    def find_all_related_jobs(self, job_name, min_common_skills: int = 3):
        """查找所有相关岗位（基于杰卡德相似度与技能重叠）"""
        query = """
        MATCH (j1:Job {name: $name})
        WITH j1, count {(j1)-[:REQUIRES]->()} AS size_A
        
        MATCH (j1)-[:REQUIRES]->(s:Skill)<-[:REQUIRES]-(j2:Job)
        WHERE j1 <> j2
        WITH size_A, j2, count(s) AS common_skills, collect(s.name) AS shared_skills
        WHERE common_skills >= $min_skills  // 粗筛：至少重合这么多技能
        
        WITH j2, common_skills, shared_skills, size_A, count {(j2)-[:REQUIRES]->()} AS size_B
        
        RETURN j2.name AS related_job,
               common_skills,
               shared_skills,
               round(toFloat(common_skills) / (size_A + size_B - common_skills), 4) AS jaccard_similarity
        ORDER BY jaccard_similarity DESC
        """
        with self.driver.session() as session:
            result = session.run(query, name=job_name, min_skills=min_common_skills)
            return [record.data() for record in result]