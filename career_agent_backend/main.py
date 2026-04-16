import json
import io
import uvicorn
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import PyPDF2
import docx

# ==========================================
# 1. 全局配置与预加载核心金库 (极速启动)
# ==========================================
# API 密钥配置
ALIYUN_API_KEY = "sk-c0a179d7f2e14776838f64bfb405a734"  # 你的千问 Key
ALIYUN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# 实例化大模型客户端
llm_client = OpenAI(api_key=ALIYUN_API_KEY, base_url=ALIYUN_BASE_URL)

print("🌟 正在加载核心基准金库...")
# 加载 51 个岗位标准画像
with open("../backend/data/standard_job_personas.json", "r", encoding="utf-8") as f:
    STANDARD_PERSONAS = json.load(f)
print(f"✅ 成功加载 {len(STANDARD_PERSONAS)} 个行业标准岗位画像！")

# 加载岗位血缘知识图谱
try:
    with open("../backend/data/job_knowledge_graph.json", "r", encoding="utf-8") as f:
        JOB_GRAPH = json.load(f)
    print(f"✅ 成功加载岗位知识图谱，包含 {len(JOB_GRAPH)} 个岗位节点！")
except FileNotFoundError:
    JOB_GRAPH = {}
    print("⚠️ 警告：未找到 job_knowledge_graph.json，图谱接口将返回空。")

# ==========================================
# 2. FastAPI 初始化与跨域配置 (CORS)
# ==========================================
app = FastAPI(title="智职领航 Backend Engine", version="2.0")

# 极其重要：允许前端网页跨域调用你的接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段允许所有前端来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 3. 数据模型定义 (Pydantic)
# ==========================================
class ManualResumeInput(BaseModel):
    basic_info: str
    skills: str
    projects: str
    internships: str = "无"
    certificates: str = "无"
    self_eval: str = "无"


class MatchRequest(BaseModel):
    student_profile: dict
    target_job: str


# ==========================================
# 4. 幕后核心引擎：大模型解析与双重打分
# ==========================================
async def analyze_resume_with_llm(resume_content: str):
    """通用核心引擎：负责将文本拆解为画像字典，并计算完整度与竞争力评分"""
    print("🚀 收到简历数据，正在呼叫大模型进行高精度拆解与打分...")

    system_prompt = """
    你是一个极其严谨的资深HR数据抽取与评估系统。请解析学生简历文本，提取能力画像并打分。
    【核心规则】
    1. 必须输出纯合法 JSON 格式，绝不包含 Markdown 标记（如 ```json），绝不说废话！
    2. 如果缺乏某项经历，对应字段填 "缺乏对应经历"，严禁脑补！
    3. JSON 必须精确包含以下键名：
       - "专业技能": (字符串)
       - "项目经历": (字符串)
       - "实习能力": (字符串)
       - "证书要求": (字符串，如四六级、软考等)
       - "学习能力": (字符串，推断其学习能力)
       - "沟通能力": (字符串，推断其沟通协调能力)
       - "创新能力": (字符串，推断其创新与解决问题能力)
       - "抗压能力": (字符串，推断其抗压能力)
       - "完整度评分": (整数 0-100，根据各项填写的饱满程度打分)
       - "竞争力评分": (整数 0-100，根据技能稀缺性和项目含金量打分)
       - "评分诊断": (用一两句话解释为何给出这两个分数，指出亮点与不足)
    """

    try:
        response = llm_client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请解析以下简历文本：\n{resume_content}"}
            ],
            temperature=0.1  # 保持极低温度，确保 JSON 结构稳定
        )

        raw_reply = response.choices[0].message.content.strip()

        # 暴力拆除可能存在的 Markdown 包装盒
        clean_text = raw_reply.replace("```json", "").replace("```", "").strip()
        parsed_json = json.loads(clean_text)

        print("✅ 大模型解析与打分成功！综合评分:", parsed_json.get("竞争力评分"))
        return {"status": "success", "data": parsed_json}

    except json.JSONDecodeError:
        print(f"❌ 大模型输出非标准 JSON，原始输出：{raw_reply}")
        raise HTTPException(status_code=500, detail="AI 解析简历格式失败，请重试")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调用大模型失败: {str(e)}")


# ==========================================
# 5. 面向前端的接口路由
# ==========================================

# --- 接口簇 A：简历录入系统 ---
@app.get("/api/resume_template")
async def get_resume_template():
    """返回简历录入模板结构，供前端渲染表单"""
    return {
        "status": "success",
        "template": {
            "basic_info": {"label": "基本信息", "placeholder": "姓名、学历、毕业院校、意向岗位..."},
            "skills": {"label": "专业技能", "placeholder": "请列出您掌握的编程语言、工具或框架..."},
            "projects": {"label": "项目经历", "placeholder": "请描述您参与过的项目名称、使用技术及您的职责..."},
            "internships": {"label": "实习/实践经历", "placeholder": "请描述您的实习经历或校园活动..."},
            "certificates": {"label": "荣誉与证书", "placeholder": "如英语四六级、软考、比赛奖项等..."},
            "self_eval": {"label": "自我评价", "placeholder": "综合描述您的学习能力、沟通能力及其他亮点..."}
        }
    }


@app.post("/api/submit_manual_resume")
async def submit_manual_resume(resume_data: ManualResumeInput):
    """处理前端提交的手动录入简历数据"""
    combined_text = f"""
    基本信息：{resume_data.basic_info}
    专业技能：{resume_data.skills}
    项目经历：{resume_data.projects}
    实习经历：{resume_data.internships}
    荣誉证书：{resume_data.certificates}
    自我评价：{resume_data.self_eval}
    """
    return await analyze_resume_with_llm(combined_text)


@app.post("/api/upload_resume_file")
async def upload_resume_file(file: UploadFile = File(...)):
    """处理前端上传的 PDF/Word 简历文件"""
    content = await file.read()
    extracted_text = ""

    try:
        filename = file.filename.lower()
        if filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text: extracted_text += text + "\n"
        elif filename.endswith(".docx"):
            doc = docx.Document(io.BytesIO(content))
            for para in doc.paragraphs:
                extracted_text += para.text + "\n"
        else:
            raise HTTPException(status_code=400, detail="仅支持上传 .pdf 或 .docx 格式的文件")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败，可能文件损坏：{str(e)}")

    if len(extracted_text.strip()) < 30:
        raise HTTPException(status_code=400, detail="未从文件中提取到足够文本，请勿上传纯图片扫描件。")

    print(f"📄 成功提取文件 {file.filename} 的文本，字数：{len(extracted_text)}")
    return await analyze_resume_with_llm(extracted_text)


# --- 接口簇 B：图谱与报告生成系统 ---
@app.get("/api/job_career_planning/{job_name}")
async def get_job_career_planning(job_name: str):
    """
    针对需求 b) 专门设计的接口：
    整合岗位关联性、行业趋势与清晰发展路径
    """
    if job_name not in JOB_GRAPH or job_name not in STANDARD_PERSONAS:
        raise HTTPException(status_code=404, detail=f"暂无【{job_name}】的规划数据")

    graph_info = JOB_GRAPH[job_name]
    persona_info = STANDARD_PERSONAS[job_name]

    # 1. 提取清晰的纵向发展路径 (对应需求中的 UI -> 资深 -> 总监)
    career_path = " -> ".join(graph_info.get("vertical", []))

    # 2. 提取岗位关联性 (横向转岗)
    transfer_opportunities = graph_info.get("transfer", [])

    return {
        "status": "success",
        "job_name": job_name,
        "planning_data": {
            # 【核心需求：路径规划】
            "development_path": {
                "steps": graph_info.get("vertical", []),
                "description": f"基于真实行业调研，您的清晰晋升路径为：{career_path}"
            },
            # 【核心需求：行业趋势】
            "industry_insight": {
                "trend": "当前该行业正向智能化、高并发架构转型，人才需求量持续增长，特别是具备全栈思维的人才。",
                "requirement_analysis": persona_info.get("专业技能", "")[:100] + "..."
            },
            # 【核心需求：岗位关联性】
            "related_jobs": transfer_opportunities,
            "planning_suggestion": f"结合您的擅长方向，除了深耕{job_name}，您还可以横向探索{', '.join([t['to'] for t in transfer_opportunities])}等关联岗位。"
        }
    }


@app.post("/api/generate_report")
async def generate_report(request: MatchRequest):
    """终极 V8 匹配引擎！生成雷达图分数与 Markdown 深度报告"""
    target_job = request.target_job
    student_profile = request.student_profile

    if target_job not in STANDARD_PERSONAS:
        raise HTTPException(status_code=400, detail=f"暂不支持岗位【{target_job}】，请从下拉列表中选择！")

    standard_persona = STANDARD_PERSONAS[target_job]
    print(f"🎯 开始为学生生成【{target_job}】深度匹配报告...")

    user_prompt = f"""
        你是一个资深的职业规划教练。请针对学生现状与目标岗位的差距，制定【个性化成长行动计划】。

        【行业标准岗位画像】：{json.dumps(standard_persona, ensure_ascii=False)}
        【求职大学生能力画像】：{json.dumps(student_profile, ensure_ascii=False)}

        【核心要求】：
        1. 必须输出合法 JSON 格式，绝不能包含 Markdown 标记。
        2. JSON 必须包含以下新字段：
           - "match_score": (总分)
           - "radar_scores": [专业技能, 通用素质, 创新能力, 学习能力]
           - "short_term_plan": {{ "period": "1-3个月", "goals": ["目标1", "目标2"], "actions": ["学习路径内容", "实践安排"] }}
           - "mid_term_plan": {{ "period": "3-12个月", "goals": ["目标1", "目标2"], "actions": ["深度项目", "实习安排"] }}
           - "evaluation_metrics": [ {{ "indicator": "指标名称", "method": "评估方式", "cycle": "评估周期" }} ]
           - "report_markdown": (包含上述内容的深度文字总结报告)
        """

    try:
        response = llm_client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": "你是一个严谨的导师，严格按 JSON 格式输出。"},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        raw_reply = response.choices[0].message.content.strip()
        clean_text = raw_reply.replace("```json", "").replace("```", "").strip()

        final_result = json.loads(clean_text)
        final_result["status"] = "success"

        print(f"✅ 匹配报告生成完毕！总匹配度: {final_result.get('match_score')}")
        return final_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成报告失败: {str(e)}")


class PolishRequest(BaseModel):
    content: str  # 待润色或检查的原始文本
    context_type: str = "report"  # 默认为报告内容，也可以是简历


@app.post("/api/polish_report")
async def polish_report(request: PolishRequest):
    """
    针对需求 d) 的核心功能：智能润色与内容完整性检查
    """
    print(f"🪄 正在对内容进行 AI 润色与合规性检查...")

    system_prompt = """
    你是一个顶级的职业发展教练。你的任务是：
    1. 润色：将用户提供的职业规划内容变得更加专业、具有行动导向。
    2. 检查：检查内容是否包含核心三要素（目标、行动、时间轴）。如果缺失，请在润色后的内容末尾予以提示。
    3. 必须保持 Markdown 格式。
    """

    try:
        response = llm_client.chat.completions.create(
            model="qwen-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请优化以下内容：\n{request.content}"}
            ],
            temperature=0.7
        )

        polished_text = response.choices[0].message.content.strip()

        # 简单模拟完整性检查逻辑
        warnings = []
        if "月" not in request.content: warnings.append("缺乏明确的时间周期")
        if "目标" not in request.content: warnings.append("职业目标描述不清晰")

        return {
            "status": "success",
            "polished_content": polished_text,
            "integrity_check": {
                "passed": len(warnings) == 0,
                "warnings": warnings
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"润色服务暂时不可用: {str(e)}")


# 模拟导出接口
@app.get("/api/export_report")
async def export_report():
    """
    针对需求 d) 的一键导出（通常前端处理下载，后端提供静态资源或文件流）
    """
    return {
        "status": "success",
        "message": "已准备好 PDF/Markdown 导出流",
        "download_url": "http://127.0.0.1:8000/static/sample_report.pdf"
    }


from typing import List, Optional


# 1. 定义报告完整性检查的模型
class ReportIntegritySchema(BaseModel):
    content: str
    required_sections: List[str] = ["短期计划", "中期计划", "评估指标", "学习路径"]


@app.post("/api/check_integrity")
async def check_integrity(request: ReportIntegritySchema):
    """
    需求 d) 核心：内容完整性检查功能
    """
    missing = []
    # 模拟简单的关键词扫描检查（实际可用 LLM 深度扫描）
    for section in request.required_sections:
        if section not in request.content:
            missing.append(section)

    return {
        "status": "success",
        "is_complete": len(missing) == 0,
        "missing_sections": missing,
        "suggestion": "请补充缺失的模块以确保规划的科学性。" if missing else "报告结构完整！"
    }


# 2. 支持手动编辑调整后的保存接口
class UpdateReportRequest(BaseModel):
    report_id: str
    updated_content: str
    user_note: Optional[str] = None


@app.post("/api/update_report")
async def update_report(request: UpdateReportRequest):
    """
    需求 d) 核心：支持手动编辑调整报告
    """
    # 这里在实际开发中会对接数据库（如 MySQL/MongoDB）
    print(f"📝 收到报告 {request.report_id} 的手动修改请求...")
    # 模拟保存成功
    return {
        "status": "success",
        "message": "报告内容已根据您的手动调整更新并固化。",
        "last_update": "2026-04-01"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)