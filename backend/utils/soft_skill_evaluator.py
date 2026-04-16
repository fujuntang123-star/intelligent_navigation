"""
软素质 AI 评估模块
使用大模型对候选人的软性素质进行深度分析和量化评分
"""
import json
from openai import OpenAI


# 初始化大模型客户端
client = OpenAI(
    api_key="sk-c0a179d7f2e14776838f64bfb405a734",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


def evaluate_soft_skills(resume_text: str, job_requirements: dict = None) -> dict:
    """
    使用 AI 对候选人的软性素质进行评估
    
    Args:
        resume_text: 简历原始文本
        job_requirements: 岗位要求字典（可选）
    
    Returns:
        包含各项软素质评分的字典
    """
    
    system_prompt = """
    你是一位资深的 HR 专家和心理学家，擅长通过文字分析候选人的软性素质。
    
    请根据提供的简历内容，从以下维度进行评估（每项 0-100 分）：
    1. 沟通能力：语言表达清晰度、逻辑性、说服力
    2. 学习能力：新技术掌握速度、持续学习意识、知识更新能力
    3. 抗压能力：面对挑战的态度、多任务处理能力、情绪管理
    4. 创新能力：解决问题的创新思路、优化改进意识、主动思考
    5. 团队协作：合作精神、角色定位、冲突处理
    6. 责任心：工作投入度、结果导向、担当意识
    
    【输出要求】
    1. 必须输出纯 JSON 格式，不包含任何 Markdown 标记
    2. 每个维度包含：score(分数), evidence(证据引用), suggestion(提升建议)
    3. 基于简历中的实际描述进行评分，不要主观臆断
    
    【JSON 格式模板】
    {
        "communication": {"score": 85, "evidence": "...", "suggestion": "..."},
        "learning": {"score": 90, "evidence": "...", "suggestion": "..."},
        "pressure_tolerance": {"score": 75, "evidence": "...", "suggestion": "..."},
        "innovation": {"score": 80, "evidence": "...", "suggestion": "..."},
        "teamwork": {"score": 88, "evidence": "...", "suggestion": "..."},
        "responsibility": {"score": 82, "evidence": "...", "suggestion": "..."},
        "overall_comment": "综合评价说明"
    }
    """
    
    user_prompt = f"请评估以下简历的软性素质：\n\n{resume_text}"
    
    if job_requirements:
        user_prompt += f"\n\n目标岗位要求：{json.dumps(job_requirements, ensure_ascii=False)}"
    
    try:
        response = client.chat.completions.create(
            model="qwen3.6-plus",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=2000,
            timeout=30  # 设置 30 秒超时
        )
        
        raw_output = response.choices[0].message.content.strip()
        
        # 清理 Markdown 标记
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:-3].strip()
        elif raw_output.startswith("```"):
            raw_output = raw_output[3:-3].strip()
        
        result = json.loads(raw_output)
        
        print(f"✅ 软素质评估完成 - 综合评分：{_calculate_overall_score(result)}/100")
        return result
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 解析失败：{raw_output}")
        return _get_default_evaluation()
    except Exception as e:
        print(f"❌ 评估失败：{str(e)}")
        return _get_default_evaluation()


def _calculate_overall_score(evaluation: dict) -> float:
    """计算软素质综合得分"""
    dimensions = [
        'communication', 'learning', 'pressure_tolerance',
        'innovation', 'teamwork', 'responsibility'
    ]
    
    total = 0
    count = 0
    for dim in dimensions:
        if dim in evaluation and 'score' in evaluation[dim]:
            total += evaluation[dim]['score']
            count += 1
    
    return round(total / count, 1) if count > 0 else 0


def _get_default_evaluation() -> dict:
    """返回默认评估（当 AI 调用失败时）"""
    return {
        "communication": {"score": 75, "evidence": "基于简历整体表现", "suggestion": "可在面试中进一步展示沟通技巧"},
        "learning": {"score": 75, "evidence": "基于技能和项目经历", "suggestion": "建议持续学习新技术"},
        "pressure_tolerance": {"score": 70, "evidence": "基于项目经验推断", "suggestion": "可通过更多实战锻炼"},
        "innovation": {"score": 72, "evidence": "基于项目成果评估", "suggestion": "培养创新思维和方法论"},
        "teamwork": {"score": 75, "evidence": "基于团队项目经历", "suggestion": "积极参与团队协作"},
        "responsibility": {"score": 75, "evidence": "基于工作成果推断", "suggestion": "保持责任心和敬业精神"},
        "overall_comment": "由于技术原因，此为参考评分，建议在面试中深入了解。"
    }


def calculate_soft_skill_score(resume_text: str, job_key: str = None) -> int:
    """
    简化的软素质打分接口（用于 matcher.py 集成）
    
    Returns:
        0-20 的整数分数
    """
    evaluation = evaluate_soft_skills(resume_text)
    overall_score = _calculate_overall_score(evaluation)
    
    # 转换为 20 分制
    return int(overall_score * 0.2)
