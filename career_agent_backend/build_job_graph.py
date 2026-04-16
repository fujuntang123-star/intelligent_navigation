import json
import itertools
import json
import pandas as pd


# 🌟 新增：加载 10000 条原始数据，作为挖掘晋升路线的矿场
print("📊 正在加载原始数据集进行垂直职级挖掘...")
df_raw = pd.read_csv("../backend/data/job_info_clean.csv")
# 1. 加载你之前炼好的 51 个标准画像
with open("../backend/data/standard_job_personas.json", "r", encoding="utf-8") as f:
    personas = json.load(f)

job_names = list(personas.keys())
job_graph = {}

print(f"🧬 正在分析 {len(job_names)} 个岗位间的血缘关系...")

for target_job in job_names:
    target_skills = personas[target_job]["专业技能"].lower()

    # 存储所有其他岗位与当前岗位的匹配分
    similarities = []

    for other_job in job_names:
        if target_job == other_job:
            continue

        other_skills = personas[other_job]["专业技能"].lower()

        # 简单的血缘算法：计算两个岗位的关键词重合度
        # 我们把字符串切成词，看重合了多少
        target_set = set(target_skills.replace(",", " ").replace("、", " ").split())
        other_set = set(other_skills.replace(",", " ").replace("、", " ").split())

        intersection = target_set.intersection(other_set)
        # 计算重合得分
        score = len(intersection)
        MIN_OVERLAP_THRESHOLD = 2
        if score >= MIN_OVERLAP_THRESHOLD:
            similarities.append({
                "to": other_job,
                "score": score,
                "reason": f"技能重合点：{', '.join(list(intersection)[:3])}等关键词高度一致"
            })

    # 按得分排序，取前 2 名作为“换岗推荐”
    top_transfers = sorted(similarities, key=lambda x: x["score"], reverse=True)[:2]

    # 模拟垂直晋升路径（这部分通常是标准化的：初级->中级->高级->专家/管理）
    # ==========================================
    # 🌟 垂直晋升路径：基于真实数据的动态挖掘
    # ==========================================
    # 1. 提取核心关键词 (脱掉外套，只留核心，如"Java开发"变成"Java")
    core_kw = target_job.replace("工程师", "").replace("人员", "").replace("专员", "").replace("开发", "").strip()

    # 2. 在 10000 条真实数据里，捞出所有包含这个关键词的岗位

    related_jobs = df_raw[df_raw['岗位名称'].str.contains(core_kw, case=False, na=False, regex=False)]['岗位名称'].dropna().tolist()

    # 3. 准备 5 个职级桶 (L1到L5)
    levels = {"L1": [], "L2": [], "L3": [], "L4": [], "L5": []}

    # 4. 根据真实岗位的命名规则，把捞出来的岗位扔进对应的桶里
    for job in related_jobs:
        if any(kw in job for kw in ["实习", "助理", "初级"]):
            levels["L1"].append(job)
        elif any(kw in job for kw in ["高级", "资深", "专家"]):
            levels["L3"].append(job)
        elif any(kw in job for kw in ["架构", "主程", "总监", "经理", "负责人", "CTO"]):
            levels["L5"].append(job)
        else:
            # 没带特殊前缀的，通常是常规级别
            levels["L2"].append(job)

    # 5. 从每个桶里挑出出现次数最多的“代表性岗位”，组成真实的晋升链条


    # 封装一个内部小函数，用来找每个桶里的"票王"
    def get_most_frequent(job_list, default_name):
        if not job_list:
            return default_name
        # 统计频次并选出最高的真实岗位名
        return max(set(job_list), key=job_list.count)


    # 依次组装 L1 -> L2 -> L3 -> L5 (L4由于概念和L3/L5常重合，精简为4步路径更清晰)
    real_l1 = get_most_frequent(levels["L1"], f"初级{core_kw}")
    real_l2 = target_job  # L2 就用当前岗位本身
    real_l3 = get_most_frequent(levels["L3"], f"高级{core_kw}")
    real_l5 = get_most_frequent(levels["L5"], f"{core_kw}负责人/总监")

    vertical_path = [real_l1, real_l2, real_l3, real_l5]

    # 清理路径中可能出现的重复项 (比如 L3 和 L5 匹配到了同一个词)
    vertical_path = list(dict.fromkeys(vertical_path))
    # ==========================================

    job_graph[target_job] = {
        "desc": personas[target_job]["专业技能"][:50] + "...",  # 截取一部分作为描述
        "vertical": vertical_path,
        "transfer": top_transfers
    }

# 2. 保存为最终的血缘图谱 JSON
with open("../backend/data/job_knowledge_graph.json", "w", encoding="utf-8") as f:
    json.dump(job_graph, f, ensure_ascii=False, indent=4)

print("🎉 岗位血缘图谱提取完毕！基于 51 个岗位的技能交叉比对生成。")