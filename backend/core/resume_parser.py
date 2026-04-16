import json
import os
import logging
from openai import AsyncOpenAI
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv(Path(__file__).parent.parent / ".env")

# 导入 Prompt 模板
from core.prompts import RESUME_PARSER_SYSTEM_PROMPT

# 配置日志
logger = logging.getLogger(__name__)

# 从环境变量读取配置
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY", ""),
    base_url=os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
)


async def parse_resume_to_json(resume_text: str) -> dict:
    """
    核心大模型解析函数：将纯文本简历解析为匹配引擎所需的标准化 JSON 画像
    """

    system_prompt = """
    你是一个资深的 HR 和数据分析师。你的任务是将用户输入的非结构化简历文本，精准解析为符合工业级标准的结构化 JSON 数据。
    
    【核心要求】
    1. 必须且只能输出合法的 JSON 字符串，绝对不要包含任何 Markdown 标记（如 ```json）或多余的解释说明文字。
    2. **严格禁止幻觉（Anti-Hallucination）**：
       - 只提取简历中**明确提到**的信息，绝对不要编造、推测或补充任何未提及的内容
       - 如果简历中没有提到学历、专业、证书等信息，对应字段必须设置为空字符串""或空数组 []
       - **绝对不要**根据工作经验、技能等间接信息推断学历或证书
       - **绝对不要**添加简历中没有的证书名称
    3. 对于无法提取的信息：
       - education: 未提及则为 ""
       - major: 未提及则为 ""
       - certificates: 未提及则为 []

    【关键指令：技能词汇归一化 (Skill Normalization)】
    为确保图数据库精准匹配，你必须对技术名词进行归一化。如："Vue 框架"统一为"Vue"；"熟练使用 Python3"统一为"Python"。
    
    **【重点】技能提取指南**：
    简历中通常会有"技能清单"、"专业技能"、"技术栈"等章节，你必须：
    1. 仔细查找这些章节，提取所有提到的技术名词
    2. 根据描述词判断掌握程度：
       - "精通" -> level: 4, level_text: "精通"
       - "熟练掌握"/"熟悉" -> level: 3, level_text: "熟悉"
       - "了解"/"知道" -> level: 2, level_text: "了解"
    3. 示例：
       - "精通 Java" -> {"name": "Java", "level": 4, "level_text": "精通"}
       - "熟悉 Python" -> {"name": "Python", "level": 3, "level_text": "熟悉"}
       - "了解 Go" -> {"name": "Go", "level": 2, "level_text": "了解"}

    **【重点】项目经验提取指南（含量化成果）**：
    简历中的项目描述通常包含具体的成果数据，你必须：
    1. 提取每个项目的名称、描述/职责
    2. **特别注意提取量化成果**：任何包含数字的结果描述，如：
       - "吞吐量提升40%" -> 提取到 description 中
       - "响应时间从800ms降低至200ms" -> 提取到 description 中
       - "团队5人" -> 提取到 description 中
    3. 如果项目提到了技术栈，提取到 tech_stack 字段
    4. description 字段要完整保留原文中的关键描述，不要过度精简

    【输出 JSON 格式模板】
    {
        "hard_thresholds": {
            "education": "提取最高学历（如：本科、硕士、大专），**如果简历中未明确提及，必须为空字符串\"\"**",
            "major": "提取专业名称，**如果简历中未明确提及，必须为空字符串\"\"**",
            "certificates": ["提取提到的证书 1", "证书 2"] **如果简历中未提及任何证书，必须为空数组 []**"
        },
        "professional_skills": [
            {
                "name": "归一化后的技能名称 (如 Java, Python, Figma)", 
                "level": 3,  # 1-4 的整数，根据掌握程度填写
                "level_text": "熟悉"  # 根据描述填写：了解、熟悉、精通
            }
        ],
        "soft_skills": [
            {
                "name": "提取软素质 (如：沟通能力, 抗压能力, 团队协作, 创新能力)",
                "score": 85
            }
        ],
        "experiences": [
            {
                "title": "项目或工作名称",
                "duration": "时长/日期",
                "description": "完整提取核心贡献和量化结果描述，保留数字和百分比"
            }
        ],
        "projects": [
            {
                "title": "项目名称",
                "description": "项目描述，**必须包含所有量化成果**（如\"吞吐量提升40%\"\"响应时间从800ms降低至200ms\"）",
                "responsibility": "个人职责描述",
                "tech_stack": "项目用到的技术栈，如\"Java, Spring Cloud, Redis, RocketMQ, MySQL, Docker\""
            }
        ]
    }
    
    【示例】
    如果简历只提到工作经验和技能，没有提到学历和证书，你应该输出：
    {
        "hard_thresholds": {
            "education": "",
            "major": "",
            "certificates": []
        },
        "professional_skills": [
            {"name": "Java", "level": 4, "level_text": "精通"},
            {"name": "Python", "level": 3, "level_text": "熟悉"},
            {"name": "Spring Boot", "level": 3, "level_text": "熟悉"}
        ],
        "projects": [
            {
                "title": "分布式电商交易平台重构",
                "description": "针对旧系统耦合度高、扩展性差的问题，基于Spring Cloud Alibaba 进行微服务拆分。负责订单中心与库存中心的设计与开发；引入RocketMQ实现削峰填谷，解决了秒杀场景下的超卖问题。",
                "responsibility": "负责订单中心与库存中心的设计与开发",
                "tech_stack": "Java, Spring Cloud, Redis, RocketMQ, MySQL, Docker"
            }
        ],
        ...
    }
    """

    user_prompt = f"请解析以下简历文本：\n\n{resume_text}"

    try:
        response = await client.chat.completions.create(
            model=os.getenv("RESUME_PARSER_MODEL", "qwen3.6-plus"),
            messages=[
                {"role": "system", "content": RESUME_PARSER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )

        raw_output = response.choices[0].message.content.strip()

        if raw_output.startswith("```json"):
            raw_output = raw_output[7:-3].strip()
        elif raw_output.startswith("```"):
            raw_output = raw_output[3:-3].strip()

        parsed_data = json.loads(raw_output)
        return parsed_data

    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析失败，大模型返回格式错误: {raw_output[:200]}")
        return {"error": "解析失败，非标准JSON格式"}
    except Exception as e:
        logger.exception(f"大模型调用发生异常: {str(e)}")
        return {"error": str(e)}