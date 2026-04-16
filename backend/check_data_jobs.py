import pandas as pd
df = pd.read_excel('data/20260226105856_457.xls')
print('所有唯一岗位名称:')
for name in df['岗位名称'].unique():
    print(f'  {name}')
