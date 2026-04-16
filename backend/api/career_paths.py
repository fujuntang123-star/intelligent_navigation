"""
职业路径规划 API 接口
提供垂直晋升路径和横向换岗路径查询
改进版：使用 app.state 中的共享 Neo4j 连接
"""
from fastapi import APIRouter, HTTPException, Request
import json
from pathlib import Path

router = APIRouter(prefix="/api", tags=["职业路径"])

# 数据文件路径
DATA_DIR = Path(__file__).parent.parent / "data"


def _get_graph(request: Request):
    """从 app.state 获取共享的 Neo4j 图数据库连接"""
    graph = getattr(request.app.state, "neo4j_graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="Neo4j 图谱服务不可用")
    return graph


@router.get("/job_career_planning/{job_name}")
async def get_job_career_planning(job_name: str, request: Request):
    """
    获取指定岗位的完整职业规划信息
    包括：垂直晋升路径、横向换岗路径、行业趋势
    """
    # 加载垂直晋升路径
    vertical_path_file = DATA_DIR / "job_vertical_paths.json"
    if not vertical_path_file.exists():
        raise HTTPException(status_code=404, detail="职业路径数据尚未初始化")

    with open(vertical_path_file, 'r', encoding='utf-8') as f:
        vertical_paths = json.load(f)

    # 加载岗位画像
    personas_file = DATA_DIR / "standard_job_personas_upgraded.json"
    if not personas_file.exists():
        raise HTTPException(status_code=404, detail="岗位画像数据不存在")

    with open(personas_file, 'r', encoding='utf-8') as f:
        personas = json.load(f)

    if job_name not in vertical_paths and job_name not in personas:
        raise HTTPException(
            status_code=404,
            detail=f"暂无【{job_name}】的规划数据，请选择其他岗位"
        )

    # 构建返回数据
    result = {
        "status": "success",
        "job_name": job_name,
        "planning_data": {}
    }

    # 1. 垂直晋升路径
    if job_name in vertical_paths:
        path_info = vertical_paths[job_name]
        career_path = " → ".join(path_info["all_related"])
        result["planning_data"]["development_path"] = {
            "steps": path_info["all_related"],
            "description": path_info.get("job_family", "") + "职业发展路径",
            "path_text": career_path
        }
    else:
        result["planning_data"]["development_path"] = {
            "steps": [job_name],
            "description": "该岗位的晋升路径数据收集中",
            "path_text": job_name
        }

    # 2. 行业洞察（优先从 Neo4j 获取）
    graph = _get_graph(request)
    try:
        with graph.driver.session() as session:
            result_db = session.run(
                "MATCH (j:Job {name: $name}) RETURN j.industry_trend AS trend, j.description AS desc",
                name=job_name
            )
            record = result_db.single()

            if record and record.get("trend"):
                trend_text = record.get("trend")
            else:
                trend_text = _get_industry_trend(job_name)

            desc_text = record.get("desc") if record and record.get("desc") else personas.get(job_name, {}).get("项目经历", "")[:200] + "..."

        result["planning_data"]["industry_insight"] = {
            "trend": trend_text,
            "key_skills": personas.get(job_name, {}).get("专业技能", [])[:5],
            "requirement_analysis": desc_text
        }
    except Exception as e:
        # 如果 Neo4j 连不上，退回到纯 JSON 模式
        if job_name in personas:
            persona = personas[job_name]
            result["planning_data"]["industry_insight"] = {
                "trend": persona.get("industry_trend", _get_industry_trend(job_name)),
                "key_skills": persona.get("专业技能", [])[:5],
                "requirement_analysis": persona.get("项目经历", "")[:200] + "..."
            }
        else:
            result["planning_data"]["industry_insight"] = {
                "trend": _get_industry_trend(job_name),
                "key_skills": [],
                "requirement_analysis": "该岗位暂无详细行业分析"
            }

    return result


@router.get("/job_transfer_paths/{job_name}")
async def get_job_transfer_paths(job_name: str, request: Request):
    """
    获取岗位的横向换岗路径（从 Neo4j 图谱查询）
    """
    try:
        graph = _get_graph(request)
        paths = graph.find_transfer_paths(job_name)

        return {
            "status": "success",
            "job_name": job_name,
            "transfer_paths": paths
        }
    except HTTPException:
        raise
    except Exception:
        # 如果 Neo4j 不可用，返回静态数据
        return {
            "status": "warning",
            "message": "Neo4j 图谱暂不可用，返回预设数据",
            "job_name": job_name,
            "transfer_paths": _get_static_transfer_paths(job_name)
        }


def _get_industry_trend(job_name: str) -> str:
    """获取行业趋势描述"""
    trends = {
        "前端开发": "当前前端技术正向智能化、工程化方向发展，大模型应用、低代码平台、跨端框架成为热点。人才需求持续增长，特别是具备全栈思维和架构能力的高级人才。",
        "Java 开发": "Java 生态持续繁荣，微服务、云原生、高并发系统架构是主流方向。企业级应用、金融科技、大数据处理等领域需求旺盛。",
        "Python 开发": "Python 在数据分析、人工智能、自动化运维等领域应用广泛。随着 AI 技术普及，Python 人才需求量持续增长。",
        "实施工程师": "数字化转型推动企业信息化系统普及，实施工程师需求稳定增长。熟悉特定行业（如制造、金融）的复合型人才更受欢迎。",
        "软件测试": "自动化测试、性能测试、安全测试成为主流。DevOps 和持续集成推动测试左移，测试开发人员缺口较大。"
    }

    return trends.get(job_name, "该行业整体发展稳定，建议关注新技术趋势和行业动向。")


def _get_static_transfer_paths(job_name: str) -> list:
    """返回预设的换岗路径（当 Neo4j 不可用时）"""
    transfer_map = {
        "前端开发": [
            {"target_job": "全栈开发", "similarity": 0.85, "common_skills": 8},
            {"target_job": "UI 设计师", "similarity": 0.65, "common_skills": 5},
            {"target_job": "产品经理", "similarity": 0.55, "common_skills": 4}
        ],
        "Java 开发": [
            {"target_job": "大数据工程师", "similarity": 0.75, "common_skills": 7},
            {"target_job": "后端架构师", "similarity": 0.80, "common_skills": 9}
        ]
    }

    return transfer_map.get(job_name, [])
