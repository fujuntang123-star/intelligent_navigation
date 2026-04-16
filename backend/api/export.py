"""
报告导出 API 接口
支持 PDF、Markdown 等格式导出
改进版：使用环境变量加载配置、移除 sys.path hack
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
import os
import logging
from pathlib import Path
from io import BytesIO
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["报告导出"])


@router.get("/export_report/{report_id}")
async def export_report_pdf(report_id: str):
    """
    导出职业规划报告为 PDF 格式
    
    Args:
        report_id: 报告 ID（实际项目中从数据库加载）
    
    Returns:
        PDF 文件流
    """
    try:
        from ..utils.pdf_export import export_report_to_pdf
        
        # 模拟报告数据（实际应从数据库加载）
        mock_report_data = {
            "target_job": "前端开发",
            "student_profile": {
                "education": "本科",
                "major": "计算机科学与技术",
                "skills": ["JavaScript", "Vue", "React"]
            },
            "match_result": {
                "total_score": 82.5,
                "details": {
                    "professional": 35.0,
                    "hard_req": 20,
                    "soft_skills": 17,
                    "project_exp": 10.5
                }
            },
            "transfer_paths": [
                {"target_job": "全栈开发", "similarity": 0.85, "common_skills": 8},
                {"target_job": "UI 设计师", "similarity": 0.65, "common_skills": 5}
            ],
            "action_plan": {
                "short_term": "深入学习 React 和 TypeScript，完成 2 个高质量项目",
                "mid_term": "掌握 Node.js 后端开发，参与开源项目贡献"
            }
        }
        
        # 生成 PDF
        pdf_buffer = export_report_to_pdf(mock_report_data)
        
        if pdf_buffer is None:
            raise HTTPException(status_code=500, detail="PDF 生成失败")
        
        # 返回文件流
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=career_report_{report_id}.pdf"
            }
        )
        
    except ImportError:
        raise HTTPException(
            status_code=503, 
            detail="PDF 导出服务未安装，请运行：pip install reportlab"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")


@router.post("/export-report/markdown")
async def export_report_markdown(report_data: dict):
    """
    将报告数据转换为 Markdown 格式
    
    Args:
        report_data: 报告数据字典
    
    Returns:
        Markdown 文本
    """
    markdown_content = generate_markdown_report(report_data)
    
    return {
        "status": "success",
        "content": markdown_content,
        "filename": f"career_report.md"
    }


@router.post("/export-report")
async def export_report_from_content(report_data: dict):
    """
    从 Markdown 内容生成 PDF
    
    Args:
        report_data: {"content": "markdown 文本"}
    
    Returns:
        PDF 文件流
    """
    try:
        from utils.pdf_export import export_report_to_pdf
        
        content = report_data.get('content', '')
        if not content:
            raise HTTPException(status_code=400, detail="报告内容为空")
        
        # 生成 PDF
        pdf_buffer = export_report_to_pdf({"content": content})
        
        if pdf_buffer is None:
            raise HTTPException(status_code=500, detail="PDF 生成失败")
        
        # 返回文件流
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=career_report.pdf"
            }
        )
        
    except ImportError as e:
        print(f"❌ ImportError: {str(e)}")
        raise HTTPException(
            status_code=503, 
            detail=f"PDF 导出服务未安装：{str(e)}"
        )
    except Exception as e:
        print(f"❌ Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败：{str(e)}")


@router.post("/polish-report")
async def polish_report(report_data: dict):
    """
    智能润色报告内容
    
    Args:
        report_data: {"content": "markdown 文本"}
    
    Returns:
        润色后的内容
    """
    try:
        content = report_data.get('content', '')
        if not content:
            raise HTTPException(status_code=400, detail="报告内容为空")
        
        # 使用 LLM 进行润色
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage
        
        llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            base_url=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            model="qwen3.6-plus",
            temperature=0.3
        )
        
        system_msg = SystemMessage(content="""
        你是一个专业的职业规划报告编辑专家。你的任务是对职业生涯发展报告进行智能润色，让报告更加专业、流畅、有说服力。
        
        润色要求：
        1. 保持 Markdown 格式不变
        2. 优化语言表达，使其更加正式和专业
        3. 增强逻辑连贯性，确保各部分衔接自然
        4. 适当添加过渡语句，使报告更易阅读
        5. 保持所有数据和事实的准确性
        6. 不要添加新的内容或数据，只优化现有表达
        
        请直接返回润色后的完整 Markdown 文本，不要添加任何额外的说明或注释。
        """)
        
        human_msg = HumanMessage(content=f"请对以下职业规划报告进行润色：\n\n{content}")
        
        response = llm.invoke([system_msg, human_msg])
        polished_content = response.content.strip()
        
        return {
            "status": "success",
            "polished_content": polished_content
        }
        
    except Exception as e:
        print(f"❌ 润色失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"润色失败：{str(e)}")


@router.post("/check-report-completeness")
async def check_report_completeness(report_data: dict):
    """
    检查报告内容完整性
    
    Args:
        report_data: {"content": "markdown 文本"}
    
    Returns:
        检查结果
    """
    try:
        content = report_data.get('content', '')
        if not content:
            raise HTTPException(status_code=400, detail="报告内容为空")
        
        # 定义报告的标准结构
        required_sections = [
            "职业探索与岗位匹配度分析",
            "综合匹配分析",
            "专业技能分析", 
            "项目经验分析",
            "软素质评估",
            "职业目标设定与职业路径规划",
            "垂直晋升路径",
            "换岗路径图谱",
            "AI 推荐的匹配岗位",
            "社会需求与行业发展趋势分析",
            "分阶段个性化成长计划",
            "评估周期与动态调整机制"
        ]
        
        # 检查各部分是否存在
        check_results = []
        for section in required_sections:
            if section in content:
                check_results.append(f"✅ {section} - 已包含")
            else:
                check_results.append(f"❌ {section} - 缺失")
        
        # 检查是否有量化数据
        has_scores = "得分" in content or "匹配度" in content
        has_recommendations = "推荐" in content
        has_plan = "计划" in content
        
        additional_checks = []
        if has_scores:
            additional_checks.append("✅ 包含量化评分")
        else:
            additional_checks.append("❌ 缺少量化评分")
            
        if has_recommendations:
            additional_checks.append("✅ 包含岗位推荐")
        else:
            additional_checks.append("❌ 缺少岗位推荐")
            
        if has_plan:
            additional_checks.append("✅ 包含发展计划")
        else:
            additional_checks.append("❌ 缺少发展计划")
        
        # 生成完整性报告
        completeness_score = (len([r for r in check_results if "✅" in r]) / len(required_sections)) * 100
        
        result_text = f"""📊 报告完整性检查结果

完整性评分: {completeness_score:.1f}/100

📋 结构完整性检查:
{chr(10).join(check_results)}

🔍 内容质量检查:
{chr(10).join(additional_checks)}

💡 建议:
- 确保所有核心章节都已包含
- 添加具体的量化数据和评分
- 包含明确的岗位推荐和发展计划
"""
        
        return {
            "status": "success",
            "check_result": result_text,
            "completeness_score": round(completeness_score, 1)
        }
        
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查失败：{str(e)}")


def generate_markdown_report(data: dict) -> str:
    """
    将报告数据转换为 Markdown 格式（辅助函数）
    
    Args:
        data: 报告数据字典
    
    Returns:
        Markdown 文本
    """
    md = "# 🚀 职业生涯发展报告\n\n"
    
    # 基本信息
    md += f"**目标岗位**: {data.get('target_job', '未指定')}\n\n"
    
    if 'student_profile' in data:
        profile = data['student_profile']
        md += "## 👤 个人画像\n\n"
        md += f"- 学历：{profile.get('education', '未填写')}\n"
        md += f"- 专业：{profile.get('major', '未填写')}\n\n"
    
    # 匹配度分析
    if 'match_result' in data:
        md += "## 🎯 人岗匹配度分析\n\n"
        match = data['match_result']
        md += f"**综合得分**: {match.get('total_score', 0)}/100\n\n"
        
        if 'details' in match:
            md += "### 维度分析\n\n"
            md += f"- 专业技能：{match['details'].get('professional', 0)}/40\n"
            md += f"- 硬性条件：{match['details'].get('hard_req', 0)}/20\n"
            md += f"- 软性素质：{match['details'].get('soft_skills', 0)}/20\n"
            md += f"- 项目经验：{match['details'].get('project_exp', 0)}/20\n\n"
    
    # 职业发展路径
    if 'transfer_paths' in data and data['transfer_paths']:
        md += "## 🛤️ 职业发展路径\n\n"
        md += "### 横向换岗机会\n\n"
        for idx, path in enumerate(data['transfer_paths'], 1):
            target = path.get('target_job', '未知')
            sim = path.get('similarity', 0)
            md += f"{idx}. **{target}** (匹配度：{sim*100:.0f}%)\n"
        md += "\n"
    
    # 行动计划
    if 'action_plan' in data:
        md += "## 📋 行动计划\n\n"
        plan = data['action_plan']
        
        if 'short_term' in plan:
            md += "### 短期计划（1-3 个月）\n\n"
            md += f"{plan['short_term']}\n\n"
        
        if 'mid_term' in plan:
            md += "### 中期计划（3-12 个月）\n\n"
            md += f"{plan['mid_term']}\n\n"
    
    md += "---\n"
    md += "*本报告由 AI 智能体生成，仅供参考*\n"
    
    return md
