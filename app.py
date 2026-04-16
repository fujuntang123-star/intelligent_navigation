import streamlit as st
import time

# ==========================================
# 1. 页面全局配置 (必须在第一行)
# 隐藏掉 Streamlit 默认的右上角菜单和底部水印，更加“白标”商业化
# ==========================================
st.set_page_config(
    page_title="AI 职业导航者 | 你的专属职场外脑",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入一点点自定义 CSS 来隐藏默认水印，提升高级感
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ==========================================
# 2. 侧边栏：操作控制台 (中枢神经)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/clouds/200/000000/artificial-intelligence.png", width=150)
    st.title("控制台设置")
    st.caption("v 1.0.0 | A13 职业规划智能体")

    st.divider()

    st.subheader("📁 个人信息载入")
    uploaded_file = st.file_uploader("拖拽上传你的简历 (PDF)", type=['pdf'])
    target_role = st.selectbox("🎯 意向岗位方向",
                               ["Python 后端开发", "算法工程师", "数据挖掘", "前端开发", "全栈工程师"])

    st.divider()

    # 模拟系统后台状态，给评委一种“底层很硬核”的感觉
    st.subheader("⚙️ 引擎状态")
    st.success("✅ FAISS 向量库已连接 (5,421 条 JD)")
    st.success("✅ 大模型推理引擎正常")

    if st.button("清空历史会话", use_container_width=True):
        st.session_state.messages = []
        st.toast("会话已重置！", icon="🗑️")

# ==========================================
# 3. 主界面：视觉看板与交互区
# ==========================================
st.title("🧭 AI 职业导航智能体")
st.markdown("基于真实大厂 JD 数据的 **千万级语料库**，为你生成精准到天的技能补强计划。")

# 使用选项卡（Tabs）将功能区分开，避免页面杂乱
tab1, tab2 = st.tabs(["💬 智能对话与规划", "📊 深度学情画像 (开发中)"])

with tab1:
    # 交互引导区
    if not uploaded_file:
        st.info("👈 请先在左侧上传简历，或直接在下方输入你的技能树开始规划。")

    # 初始化聊天历史
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant",
                                      "content": "你好！我已经准备好为你拆解真实岗位的核心需求了。告诉我你的专业和目前掌握的技术吧！"}]

    # 渲染历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 聊天输入框
    if prompt := st.chat_input("例如：我是软工大三学生，会 Python 和 SQL，怎么准备秋招？"):
        # 记录用户输入
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 思考与回复区
        with st.chat_message("assistant"):
            # 添加炫酷的加载动画
            with st.spinner('🧠 正在检索底层向量库并进行知识比对...'):
                time.sleep(1.5)  # 模拟网络延迟

            # 使用 Expander 折叠展示检索过程 (高级感拉满！)
            with st.expander("🔍 查看 AI 检索思考过程"):
                st.caption("- 提取用户特征：Python, SQL, 大三秋招")
                st.caption(f"- 命中高频相关 JD：78 条 (方向：{target_role})")
                st.caption("- 正在执行 RAG 信息融合与差异比对...")

            # 模拟结构化的优质排版输出
            mock_reply = f"""
            基于你提供的技能以及对 **{target_role}** 的岗位检索，我为你生成了以下核心规划：

            ### 🚨 核心技能差距诊断
            * **强项：** 具备 Python 与 SQL 基础，跨过了后端开发的基本门槛。
            * **痛点：** 缺乏完整的项目工程化经验（如 Git 协作、Docker 部署）以及主流 Web 框架（FastAPI/Django）的实战。

            ### 🗺️ 突击学习路径
            1. **第一阶段：框架筑基 (1-2周)**
               * 重点攻克 `FastAPI`，理解路由、依赖注入与异步处理。
            2. **第二阶段：组件进阶 (3-4周)**
               * 结合 SQL，引入 `Redis` 解决高并发场景下的缓存问题。
            3. **第三阶段：工程落地 (考前1周)**
               * 学习手写 `Dockerfile`，将你的项目跑在 Linux 容器中。

            > 💡 **面试官 Tip:** 在简历中重点突出你在第二阶段遇到的缓存击穿/穿透问题是如何解决的。
            """

            # 动态打字机效果输出
            message_placeholder = st.empty()
            full_response = ""
            for chunk in mock_reply.split('\n'):
                full_response += chunk + "\n"
                time.sleep(0.1)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)

            # 记录 AI 回复
            st.session_state.messages.append({"role": "assistant", "content": full_response})

with tab2:
    # 这里可以放一些假的数据看板，给评委画个饼
    st.subheader("能力维度雷达图")
    st.markdown("这里后续可以接入 `echarts` 或 Streamlit 原生的图表库，展示学生的各项能力雷达图，提升系统的商业价值。")
    # 模拟数据指标展示
    col1, col2, col3 = st.columns(3)
    col1.metric("简历竞争力评分", "72/100", "击败 45% 同学")
    col2.metric("技能匹配度", "68%", "-12% (距头部大厂)")
    col3.metric("预计补强耗时", "45 天", "高强度")