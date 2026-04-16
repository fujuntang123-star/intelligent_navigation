import pandas as pd
import numpy as np

try:
    # 读取那 10000 条岗位数据
    df_jobs = pd.read_excel("data/20260226105856_457.xls")
    print(f"📊 成功挂载数据集！共检测到 {len(df_jobs)} 条岗位信息。")
except Exception as e:
    print(f"⚠️ 警告：未找到数据文件，将使用模拟数据运行。错误: {e}")
    df_jobs = None

df_jobs.info()
print(df_jobs.columns)
print(df_jobs.head())
print(df_jobs.iloc[:]["岗位名称"])
