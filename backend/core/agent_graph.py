import json
import os
import sys
import asyncio
from pathlib import Path
from typing import TypedDict, Annotated, Sequence
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

# 加载 .env 环境变量
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# 导入 Prompt 模板
from core.prompts import CAREER_REPORT_SYSTEM_PROMPT, CAREER_REPORT_USER_PROMPT_TEMPLATE

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

# 导入我们的底层基建
from matcher import MatchEngine
from graph.graph_builder import CareerGraph
from resume_parser import parse_resume_to_json


# ==========================================
# 1. 定义全局状态 (TypedDict)
# ==========================================
class CareerState(TypedDict):
    resume_text: str  # 用户输入的简历原始文本
    target_job: str  # 目标岗位
    student_profile: dict  # 解析后的结构化画像
    match_score: dict  # 匹配打分结果
    transfer_paths: list  # 换岗路径数据
    recommended_jobs: list  # 推荐的匹配岗位
    enhanced_career_paths: list  # 增强版的岗位关联图谱
    report_draft: str  # 最终生成的报告内容
    error: str  # 记录可能出现的错误


# ==========================================
# 2. 初始化底层引擎与大模型
# ==========================================
# 注意：matcher_engine 将由 main.py 注入（带 Excel 数据的实例）
_matcher_engine = None  # 在 main.py 中通过 set_matcher_engine() 注入

def set_matcher_engine(engine):
    """由 main.py 调用，注入带Excel数据的匹配引擎实例"""
    global _matcher_engine
    _matcher_engine = engine
    print(f"✅ agent_graph 已注入匹配引擎实例")

def get_matcher_engine():
    """获取匹配引擎实例，如果未注入则懒加载一个默认实例"""
    global _matcher_engine
    if _matcher_engine is None:
        from pathlib import Path
        personas_path = Path(__file__).parent.parent / "data" / "standard_job_personas_upgraded.json"
        excel_path = Path(__file__).parent.parent / "data" / "20260226105856_457.xls"
        if personas_path.exists():
            _matcher_engine = MatchEngine(excel_path=excel_path if excel_path.exists() else None, use_rag=True)
        else:
            _matcher_engine = MatchEngine()
    return _matcher_engine

# 向后兼容：提供全局变量名
matcher_engine = None  # 将在节点函数中通过 get_matcher_engine() 动态获取

# 注意：Neo4j 连接信息从环境变量读取
neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
neo4j_user = os.getenv("NEO4J_USER", "neo4j")
neo4j_password = os.getenv("NEO4J_PASSWORD", "12345678")
neo4j_graph = CareerGraph(neo4j_uri, neo4j_user, neo4j_password)

# 从环境变量读取 LLM 配置
llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", ""),
    base_url=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    model=os.getenv("MODEL_NAME", "qwen3.6-plus"),
    temperature=0.7
)


# ==========================================
# 3. 封装智能体工具 (Tools)
# ==========================================
@tool
def tool_calculate_match_score(student_profile: str, target_job: str) -> str:
    """工具 1：计算人岗匹配得分。当你需要评估候选人与目标岗位的匹配度时调用此工具。"""
    try:
        profile_dict = json.loads(student_profile)
        # 适配 matcher 需要的字典格式
        formatted_skills = {s['name']: s.get('level_text', '熟悉') for s in profile_dict.get('professional_skills', [])}
        profile_dict['skills'] = formatted_skills

        engine = get_matcher_engine()
        result = engine.calculate_score(profile_dict, target_job)
        return json.dumps(result, ensure_ascii=False) if result else "未找到该岗位标准画像"
    except Exception as e:
        return f"打分失败：{str(e)}"


@tool
def tool_recommend_jobs(student_profile: str, top_n: int = 5) -> str:
    """工具 3：推荐匹配岗位。根据候选人画像推荐最匹配的多个岗位。当你需要为候选人推荐适合的岗位列表时调用此工具。"""
    try:
        profile_dict = json.loads(student_profile)
        # 适配 matcher 需要的字典格式
        formatted_skills = {s['name']: s.get('level_text', '熟悉') for s in profile_dict.get('professional_skills', [])}
        profile_dict['skills'] = formatted_skills

        engine = get_matcher_engine()
        recommendations = engine.recommend_jobs(profile_dict, top_n)
        return json.dumps(recommendations, ensure_ascii=False)
    except Exception as e:
        return f"推荐失败：{str(e)}"


@tool
def tool_query_career_path(target_job: str) -> str:
    """工具2：查询 Neo4j 获取岗位的晋升与换岗路径。当你需要为候选人规划职业发展路线时调用此工具。"""
    try:
        paths = neo4j_graph.find_transfer_paths(target_job)
        return json.dumps(paths, ensure_ascii=False)
    except Exception as e:
        return f"图谱查询失败: {str(e)}"


# ==========================================
# 4. 定义图的节点 (Nodes)
# ==========================================
async def node_parse_resume(state: CareerState):
    """节点1：大模型解析简历提取画像"""
    print("📍 [节点] 正在解析简历生成学生画像...")
    
    # 【新增判断】：如果状态里已经有了解析好的画像，直接跳过大模型调用！
    if state.get("student_profile") and not state.get("student_profile").get("error"):
        print("⚡ 检测到已解析的画像，跳过重复大模型调用！")
        return {"student_profile": state["student_profile"]}
        
    profile = await parse_resume_to_json(state["resume_text"])
    if "error" in profile:
        return {"error": profile["error"]}
    return {"student_profile": profile}


async def node_gather_intelligence(state: CareerState):
    """节点 2：收集情报 (并发执行查询，加速响应)"""
    print("📍 [节点] 智能体正在查询图谱与计算匹配得分...")
    if state.get("error"):
        return state

    try:
        profile_dict = state["student_profile"]
        profile_dict['resume_text'] = state.get('resume_text', '')
        formatted_skills = {s['name']: s.get('level_text', '熟悉') for s in profile_dict.get('professional_skills', [])}
        profile_dict['skills'] = formatted_skills

        # 并发执行三个独立查询
        async def calc_score():
            engine = get_matcher_engine()
            return engine.calculate_score(profile_dict, state["target_job"])

        async def recommend():
            engine = get_matcher_engine()
            return engine.recommend_jobs(profile_dict, top_n=5, use_rag=True)

        async def find_transfer():
            try:
                return neo4j_graph.find_transfer_paths(state["target_job"], top_n=5)
            except Exception as e:
                print(f"⚠️ 查询换岗路径失败：{str(e)}")
                return []

        # 并发执行
        match_result, recommendations, transfer_paths = await asyncio.gather(
            calc_score(), recommend(), find_transfer()
        )

        # 查询推荐岗位的垂直路径（并行）
        async def get_vertical(rec_job):
            job_name = rec_job['job_name']
            try:
                vertical = neo4j_graph.find_vertical_paths(job_name)
                return {'job_name': job_name, 'match_score': rec_job['total_score'], 'vertical_paths': vertical}
            except Exception as e:
                print(f"⚠️ 查询 {job_name} 的垂直路径失败：{str(e)}")
                return {'job_name': job_name, 'match_score': rec_job['total_score'], 'vertical_paths': []}

        enhanced_paths = await asyncio.gather(*[get_vertical(r) for r in recommendations[:3]])

        return {
            "match_score": match_result or {},
            "transfer_paths": transfer_paths or [],
            "recommended_jobs": recommendations or [],
            "enhanced_career_paths": list(enhanced_paths)
        }
    except Exception as e:
        print(f"❌ 节点 2 执行失败：{str(e)}")
        return {
            "match_score": {},
            "transfer_paths": [],
            "recommended_jobs": [],
            "enhanced_career_paths": [],
            "error": f"情报收集失败：{str(e)}"
        }


async def node_draft_report(state: CareerState):
    """节点 3：撰写报告 (大模型基于收集到的上下文撰写最终报告)"""
    print("📍 [节点] 智能体正在像写论文一样撰写《职业生涯发展报告》...")
    if state.get("error"):
        return {"report_draft": f"生成失败：{state['error']}"}

    sys_msg = SystemMessage(content=CAREER_REPORT_SYSTEM_PROMPT)

    # 提取最匹配岗位的公司推荐数据
    positions_data = ""
    if state.get('recommended_jobs'):
        sorted_jobs = sorted(state['recommended_jobs'], key=lambda x: x.get('total_score', 0), reverse=True)
        if sorted_jobs:
            best_job = sorted_jobs[0]
            positions = best_job.get('recommended_positions', [])
            if positions:
                positions_data = "\n| 公司名称 | 薪资范围 | 匹配度 | 推荐理由 |\n|----------|----------|--------|----------|\n"
                for pos in positions[:3]:
                    company = pos.get('company', '未知公司')
                    salary = pos.get('salary', '面议')
                    similarity = pos.get('similarity', 0)
                    positions_data += f"| {company} | {salary} | {similarity:.0f}% | 你的技能与岗位要求高度匹配 |\n"
    
    if not positions_data:
        positions_data = "\n| 公司名称 | 薪资范围 | 匹配度 | 推荐理由 |\n|----------|----------|--------|----------|\n| 暂无数据（待补充） | 面议 | - | - |\n"
    
    print(f"\n🔍 传递给 LLM 的公司推荐数据：")
    print(positions_data)

    # 使用提取的 Prompt 模板
    prompt = CAREER_REPORT_USER_PROMPT_TEMPLATE.format(
        student_profile=json.dumps(state['student_profile'], ensure_ascii=False),
        target_job=state['target_job'],
        match_score=json.dumps(state['match_score'], ensure_ascii=False),
        transfer_paths=json.dumps(state['transfer_paths'], ensure_ascii=False),
        recommended_jobs=json.dumps(state['recommended_jobs'], ensure_ascii=False),
        enhanced_career_paths=json.dumps(state['enhanced_career_paths'], ensure_ascii=False),
        positions_data=positions_data
    )

    # 使用异步 LLM 生成报告
    response = await llm.ainvoke([sys_msg, HumanMessage(content=prompt)])
    full_report = response.content if hasattr(response, 'content') else str(response)
    
    print(f"📝 报告生成完成，长度: {len(full_report)}")
    return {"report_draft": full_report}


# ==========================================
# 5. 编排 LangGraph 图 (Workflow)
# ==========================================
def build_career_agent():
    workflow = StateGraph(CareerState)

    # 1. 注册节点
    workflow.add_node("parse", node_parse_resume)
    workflow.add_node("research", node_gather_intelligence)
    workflow.add_node("draft", node_draft_report)

    # 2. 定义边 (定义状态流转逻辑)
    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "research")
    workflow.add_edge("research", "draft")
    workflow.add_edge("draft", END)

    # 3. 编译图
    return workflow.compile()


# 实例化全局单例供 FastAPI 使用
career_agent_app = build_career_agent()