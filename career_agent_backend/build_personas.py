import pandas as pd
import json
import time
from openai import OpenAI

# 1. 初始化千问大模型客户端 (建议用 qwen-turbo)
client = OpenAI(
    api_key="sk-c0a179d7f2e14776838f64bfb405a734",  # 替换为你的秘钥
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# 定义完美的系统 Prompt，强制定制 10 维画像
system_prompt = """
你是一个资深的 HR 数据分析专家。请根据我提供的多份真实岗位详情样本，提炼出该岗位的【通用标准画像】。
【核心规则】
1. 你必须只输出合法的 JSON 格式字符串，不要包含 ```json 等 Markdown 标记，不要说废话。
2. JSON 必须严格包含以下 10 个键名，值为字符串格式（除了评分）：
   - "岗位名称": (当前分析的岗位名)
   - "专业技能": (提炼核心硬技能、编程语言、工具等)
   - "项目经历": (该岗位通常需要什么样的项目实战经验)
   - "证书要求": (加分证书，如无则填"无特殊要求")
   - "创新能力": (该岗位需要的解决问题/创新思维能力)
   - "学习能力": (对新技术学习能力的要求)
   - "抗压能力": (高并发、加班或复杂环境下的抗压要求)
   - "沟通能力": (跨部门协作、沟通交流能力要求)
   - "实习能力": (对实习或相关工作经验的通用要求)
   - "竞争力基准分": (整数 0-100，评估该岗位的行业整体门槛难度，如算法工程师填90，普通测试填70)
"""

print("🧹 正在加载纯净版数据集...")
df = pd.read_csv("../backend/data/job_info_clean.csv")

# 获取 51 个独立岗位
unique_jobs = df['岗位名称'].unique().tolist()
print(f"🎯 共发现 {len(unique_jobs)} 个独立岗位，准备启动批量画像提炼！")

# 用来存放最终所有画像的字典
all_personas = {}

for index, job_name in enumerate(unique_jobs, 1):
    print(f"\n⏳ [{index}/{len(unique_jobs)}] 正在为【{job_name}】提炼标准画像...")

    # 筛选出当前岗位的所有数据
    job_data = df[df['岗位名称'] == job_name]

    # 为了省 Token 且高效，我们随机抽取最多 10 条该岗位的详情作为样本
    sample_texts = job_data['岗位详情'].dropna().head(10).tolist()

    # 把这 10 条详情拼成一段长文本喂给大模型
    merged_description = "\n---\n".join(sample_texts)

    user_prompt = f"请根据以下多个企业对【{job_name}】的真实要求，提炼出该岗位的标准十维画像。\n\n企业真实要求样本：\n{merged_description}"

    try:
        # 呼叫大模型
        response = client.chat.completions.create(
            model="qwen-turbo",  # 使用 qwen-turbo，速度快且免费额度高
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3  # 降低发散性，保证 JSON 格式严格
        )

        # 获取结果并清洗 Markdown 标记
        result_str = response.choices[0].message.content.strip()
        if result_str.startswith("```json"):
            result_str = result_str[7:-3].strip()
        elif result_str.startswith("```"):
            result_str = result_str[3:-3].strip()

        # 解析 JSON 并存入大字典
        persona_json = json.loads(result_str)
        all_personas[job_name] = persona_json
        print(f"✅ 【{job_name}】画像提炼成功！")

    except Exception as e:
        print(f"❌ 【{job_name}】提炼失败，跳过。错误信息：{e}")

    # 【极其重要】每次请求完休眠 2 秒，防止触发阿里云 API 的并发限流报错！
    time.sleep(2)

# 所有岗位跑完后，统一保存为终极 JSON 数据库
output_file = "../backend/data/standard_job_personas.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(all_personas, f, ensure_ascii=False, indent=4)

print(f"\n🎉🎉🎉 壮举完成！51 个岗位的标准十维画像已全部保存至：{output_file}")