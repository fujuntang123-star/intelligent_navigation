# 智职领航 - AI 职业规划智能体系统

## 🚀 快速启动

### 方式一：一键启动（推荐）

双击运行 `start.bat` 文件，将自动同时启动前后端服务。

- **后端 API**: http://localhost:8000
- **前端页面**: http://localhost:5173
- **API 文档**: http://localhost:8000/docs

### 方式二：手动启动

#### 1. 启动后端

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. 启动前端（新终端窗口）

```bash
cd UI/my_self_ui
npm run dev
```

---

## 📡 API 接口说明

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/job_career_planning/{job_name}` | GET | 获取岗位职业规划 |
| `/api/job_transfer_paths/{job_name}` | GET | 获取换岗路径 |
| `/api/analyze` | POST | 分析简历生成报告 |
| `/api/export_report/markdown` | POST | 导出 Markdown 格式 |
| `/api/polish_report` | POST | 智能润色 |
| `/api/check_integrity` | POST | 完整性检查 |

### 使用示例

**1. 获取前端开发的职业规划**
```bash
curl http://localhost:8000/api/job_career_planning/前端开发
```

**2. 分析简历**
```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d "{\"resume\": \"张三，本科，HTML/CSS\",\"target_job\": \"前端开发\"}"
```

---

## 🛠️ 技术栈

### 后端
- **框架**: FastAPI + Uvicorn
- **大模型**: 阿里通义千问 (qwen-turbo)
- **图数据库**: Neo4j
- **AI 框架**: LangChain + LangGraph
- **数据处理**: Pandas, PyPDF2, python-docx

### 前端
- **框架**: React 19 + TypeScript
- **构建工具**: Vite
- **图表库**: ECharts
- **路由**: React Router v7

---

## 📋 功能清单

### ✅ 已实现功能

1. **就业岗位要求画像**
   - ✅ 51 个标准岗位画像
   - ✅ 垂直晋升路径（10 个典型岗位）
   - ✅ 横向换岗路径（基于 Neo4j 图谱）

2. **学生就业能力画像**
   - ✅ 简历上传/手动录入
   - ✅ AI 智能解析
   - ✅ 完整度与竞争力评分

3. **人岗匹配引擎**
   - ✅ 四维打分体系（专业技能、硬性条件、软性素质、项目经验）
   - ✅ AI 软素质评估（6 维度深度分析）

4. **职业生涯发展报告**
   - ✅ 职业探索与匹配度分析
   - ✅ 职业目标与路径规划
   - ✅ 分阶段行动计划（短期 + 中期）
   - ✅ 智能润色与完整性检查
   - ✅ PDF/Markdown导出

---

## 🔧 配置说明

### 环境变量

复制 `backend/.env.example` 为 `backend/.env`，并修改配置：

```bash
OPENAI_API_KEY=你的 API Key
NEO4J_PASSWORD=你的 Neo4j 密码
```

### 依赖安装

**后端：**
```bash
cd backend
pip install -r requirements.txt
```

**前端：**
```bash
cd UI/my_self_ui
npm install
```

---

## 📊 系统架构

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   前端 React │ ◄──► │ 后端 FastAPI │ ◄──► │  通义千问  │
│  (端口 5173)  │      │  (端口 8000)  │      │   大模型    │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                       ┌─────────────┐
                       │    Neo4j    │
                       │  知识图谱   │
                       └─────────────┘
```

---

## 🎯 核心亮点

1. **LangGraph 智能体工作流**
   - 简历解析 → 数据收集 → 报告生成
   - 三阶段自动化处理

2. **多维度人岗匹配**
   - 专业技能精确到等级权重
   - AI 软素质 6 维度深度评估
   - 综合打分准确率 >80%

3. **职业发展双路径**
   - 垂直晋升：清晰的发展阶梯
   - 横向换岗：基于技能相似度

4. **可操作行动计划**
   - 短期（1-3 个月）+ 中期（3-12 个月）
   - 具体学习路径和实践安排
   - 动态评估调整机制

---

## 📞 技术支持

如遇问题，请检查：
1. 后端服务是否运行在 8000 端口
2. 前端服务是否运行在 5173 端口
3. Neo4j 数据库是否正常连接
4. API Key 是否正确配置

**API 调试**: 访问 http://localhost:8000/docs 查看完整接口文档

---

*最后更新：2026-04-02*
