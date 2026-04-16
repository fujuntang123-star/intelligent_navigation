import re

# 读取文件
with open(r'D:\contest\UI\chat-app\src\components\ChatInterface.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 在 analyzeJobMode 函数开头添加 setIsThinking(true)
content = re.sub(
    r'(const analyzeJobMode = async \(resumeText\) => \{\s*// 记录请求开始时间\s*const requestStartTime = Date\.now\(\);)\s*(// 记录当前正在流式输出的会话 ID)',
    r'\1\n\n    // 设置 AI 为思考状态\n    setIsThinking(true);\n\n    \2',
    content
)

# 2. 修改消息文本
content = re.sub(
    r"content: '🔍 正在分析简历并生成职业规划报告\.\.\.'",
    "content: '正在匹配岗位...'",
    content
)

# 3. 在 done 事件中添加 setIsThinking(false)
content = re.sub(
    r"(console\.log\('✅ 报告生成完成，总长度:', accumulatedContent\.length\);)\s*(streamingConversationIdRef\.current = null;)",
    r'\1\n                setIsThinking(false);\n                \2',
    content
)

# 4. 在 error 事件中添加 setIsThinking(false)
content = re.sub(
    r"(msg\.id === reportMsgId \? \{ \.\.\.msg, content: `❌ 错误：\$\{data\.message\}`, responseTime: parseFloat\(errorResponseTime\) \} : msg\s*\)\s*, sourceConvId\);)\s*(streamingConversationIdRef\.current = null;)",
    r'\1\n                setIsThinking(false);\n                \2',
    content
)

# 5. 在 catch 块中添加 setIsThinking(false)
content = re.sub(
    r"(streamingConversationIdRef\.current = null;\s*\}\s*\};)",
    r"\1\n      setIsThinking(false);",
    content,
    count=1
)

# 6. 修改 AI 头像渲染部分，添加微光转动动画
old_avatar = '''              msg.role === 'ai' ? (
                <div key={msg.id} className="flex gap-4 group" data-msg-id={msg.id}>
                  <div className="w-8 h-8 rounded-full bg-purple-100 flex items-center justify-center text-xl shrink-0">✨</div>'''

new_avatar = '''              msg.role === 'ai' ? (
                <div key={msg.id} className="flex gap-4 group" data-msg-id={msg.id}>
                  {/* AI 头像 - 思考时显示微光转动效果 */}
                  <div className={`relative w-8 h-8 shrink-0 ${
                    isThinking && msg.content?.includes('正在匹配岗位') ? 'animate-pulse' : ''
                  }`}>
                    {/* 头像主体 */}
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xl z-10 ${
                      isThinking && msg.content?.includes('正在匹配岗位')
                        ? 'bg-purple-200'
                        : 'bg-purple-100'
                    }`}>
                      ✨
                    </div>
                    {/* 微光转动环 - 仅在思考时显示 */}
                    {isThinking && msg.content?.includes('正在匹配岗位') && (
                      <div className="absolute inset-0 rounded-full animate-spin" style={{
                        background: 'conic-gradient(from 0deg, transparent 0%, rgba(147, 51, 234, 0.8) 50%, transparent 100%)',
                        animationDuration: '1.5s',
                      }} />
                    )}
                    {/* 思考时的呼吸光晕 */}
                    {isThinking && msg.content?.includes('正在匹配岗位') && (
                      <div className="absolute inset-0 rounded-full bg-purple-400 animate-pulse opacity-40 z-0" />
                    )}
                  </div>'''

content = content.replace(old_avatar, new_avatar)

# 写入文件
with open(r'D:\contest\UI\chat-app\src\components\ChatInterface.jsx', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 文件修改成功！")
