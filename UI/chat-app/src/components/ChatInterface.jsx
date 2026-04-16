import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';
import { apiService } from '../services/api';
import html2pdf from 'html2pdf.js';

// AI 头像路径（将自定义头像放入 public/avatars/ 目录即可）
const AI_AVATAR_URL = '/avatars/image.png';

const ChatInterface = () => {
  // ================= 会话管理 =================
  // 从 localStorage 加载历史会话
  const loadConversations = () => {
    try {
      const saved = localStorage.getItem('career_conversations');
      if (saved) {
        return JSON.parse(saved);
      }
    } catch (e) {
      console.error('加载会话失败:', e);
    }
    return [];
  };

  // 会话列表（每个会话包含 id, name, messages, mode, 等）
  const [conversations, setConversations] = useState(loadConversations);
  // 当前活跃的会话 ID
  const [activeConversationId, setActiveConversationId] = useState(() => {
    const saved = loadConversations();
    return saved.length > 0 ? saved[0].id : null;
  });
  // 会话项的三点菜单状态
  const [conversationMenuId, setConversationMenuId] = useState(null);
  // 会话标题菜单状态
  const [titleMenuOpen, setTitleMenuOpen] = useState(false);
  
  // 控制菜单和弹窗的状态
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isFormModalOpen, setIsFormModalOpen] = useState(false);
  const [isResumeModalOpen, setIsResumeModalOpen] = useState(false); // 简历选择弹窗
  
  // 用户简历信息
  const [resumeData, setResumeData] = useState(null);
  const [attachedFile, setAttachedFile] = useState(null); // 附件文件
  
  // 咨询模式的岗位数据
  const [jobList, setJobList] = useState([]);
  
  // 当前模式（job | consult | null）
  const [currentMode, setCurrentMode] = useState(null);

  // ================= 当前会话的消息 =================
  const initialMessages = [
    { 
      id: 1, 
      role: 'ai', 
      content: '你好！我是你的智能就业导师。你可以：\n\n📄 **上传简历** - 支持 PDF、Word 格式，我会为你分析并推荐岗位\n💬 **咨询岗位** - 告诉我你想了解的岗位或行业\n🎯 **职业规划** - 为你制定个性化的发展路径\n\n请随时告诉我你的需求！'
    }
  ];

  // 从当前活跃会话加载消息
  const [messages, setMessages] = useState(() => {
    const convs = loadConversations();
    const active = convs.find(c => c.id === activeConversationId);
    return active ? active.messages : initialMessages;
  });

  // 求职意向数据
  const [jobIntention, setJobIntention] = useState({
    education: '',
    industry: '',
    position: ''
  });

  // 简历表单数据
  const [resumeForm, setResumeForm] = useState({
    name: '',
    contact: '',
    intention: '',
    other: '',
    school: '',
    major: '',
    schoolTime: '',
    schoolInfo: '',
    company: '',
    role: '',
    description: '',
    skills: '',
    certificates: '',
    awards: '',
    selfEval: ''
  });

  // 生成唯一 ID（避免 Date.now() 在毫秒内重复）
  const idCounter = useRef(0);
  const chatContainerRef = useRef(null);
  // 用 ref 跟踪当前活跃的会话 ID，避免闭包问题
  const activeConversationIdRef = useRef(activeConversationId);
  // 跟踪当前正在流式输出的会话 ID（防止切换会话后写入错误的会话）
  const streamingConversationIdRef = useRef(null);
  // 跟踪流式输出是否正在进行
  const isStreamingRef = useRef(false);
  // 跟踪 AI 是否在思考中（用于头像动画）
  const [isThinking, setIsThinking] = useState(false);
  // 用 ref 实时跟踪每个会话的最新消息，避免切换时读取到旧状态
  const conversationsRef = useRef(conversations);

  const generateId = () => {
    idCounter.current += 1;
    return `${Date.now()}-${idCounter.current}`;
  };

  // 用于 PDF 导出的 ref
  const reportContentRef = useRef(null);

  // 同步 activeConversationId 到 ref
  useEffect(() => {
    activeConversationIdRef.current = activeConversationId;
  }, [activeConversationId]);

  // 同步 conversations 到 ref 和 localStorage
  useEffect(() => {
    conversationsRef.current = conversations;
    try {
      localStorage.setItem('career_conversations', JSON.stringify(conversations));
    } catch (e) {
      console.error('保存会话失败:', e);
    }
  }, [conversations]);

  // 智能总结会话标题
  const generateConversationTitle = (messages) => {
    if (!messages || messages.length === 0) return '新的对话';
    
    // 找到第一条用户消息
    const firstUserMsg = messages.find(m => m.role === 'user');
    if (!firstUserMsg) return '新的对话';
    
    const content = firstUserMsg.content;
    
    // 规则1: 简历相关
    if (content.includes('简历') || content.includes('提交简历') || content.includes('上传简历')) {
      return '简历分析';
    }
    
    // 规则2: 岗位推荐/匹配
    if (content.includes('推荐') || content.includes('匹配') || content.includes('求职意向')) {
      return '岗位推荐';
    }
    
    // 规则3: 职业规划
    if (content.includes('职业规划') || content.includes('发展规划') || content.includes('发展路径')) {
      return '职业规划';
    }
    
    // 规则4: 咨询相关
    if (content.includes('咨询') || content.includes('了解') || content.includes('问问')) {
      return '岗位咨询';
    }
    
    // 规则5: 面试相关
    if (content.includes('面试') || content.includes('offer')) {
      return '面试准备';
    }
    
    // 默认: 提取关键词生成简短标题
    // 移除常见语气词和助词
    const cleaned = content
      .replace(/^(你好|您好|嗨|嘿|请问|我想|帮我|给我|查询|搜索)/, '')
      .trim();
    
    // 取前15个字符作为标题
    return cleaned.substring(0, 15) || '新的对话';
  };

  // 更新当前会话的消息（支持直接值或函数式更新）
  // targetConvId 可选参数：指定要更新的会话 ID（用于流式输出时锁定目标会话）
  const updateCurrentConversation = (updater, targetConvId = null) => {
    const currentId = targetConvId || activeConversationIdRef.current;

    // 只更新 conversations 状态一次，不嵌套调用
    setConversations(prev => {
      return prev.map(conv => {
        if (conv.id === currentId) {
          const newMsgs = typeof updater === 'function' ? updater(conv.messages) : updater;
          return {
            ...conv,
            messages: newMsgs,
            name: generateConversationTitle(newMsgs),
            updatedAt: new Date().toISOString()
          };
        }
        return conv;
      });
    });
  };

  // 同步当前活跃会话的消息到 messages 状态（流式输出和切换会话时都会触发）
  useEffect(() => {
    // 如果正在流式输出到其他会话，不要覆盖当前视图
    if (streamingConversationIdRef.current && streamingConversationIdRef.current !== activeConversationId) {
      return;
    }
    const activeConv = conversationsRef.current.find(c => c.id === activeConversationId);
    if (activeConv && activeConv.messages) {
      setMessages(activeConv.messages);
    }
  }, [conversations, activeConversationId]); // 监听 conversations 和 activeConversationId

  // 自动滚动到底部
  useEffect(() => {
    console.log('📊 当前消息数量:', messages.length);
    if (chatContainerRef.current) {
      // 使用 requestAnimationFrame 确保 DOM 更新后再滚动
      requestAnimationFrame(() => {
        chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
      });
    }
  }, [messages]);

  // ================= 创建新会话 =================
  const handleNewChat = () => {
    console.log('🔄 创建新会话');
    const newId = `conv_${Date.now()}`;
    const newConversation = {
      id: newId,
      name: '新的对话',
      mode: null,
      messages: initialMessages,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    setConversations(prev => [newConversation, ...prev]);
    setActiveConversationId(newId);
    setMessages(initialMessages);
    setCurrentMode(null);
    setResumeData(null);
    setJobIntention({
      education: '',
      industry: '',
      position: ''
    });
    console.log('✅ 已创建新会话:', newId);
  };

  // ================= 切换到指定会话 =================
  const switchToConversation = (convId) => {
    if (convId === activeConversationId) return;

    // 优先从 ref 读取最新的会话数据（包含未提交的流式更新）
    const conv = conversationsRef.current.find(c => c.id === convId);
    if (conv) {
      console.log('🔄 切换会话: 从', activeConversationId, '到', convId, '消息数量:', conv.messages.length);
      // 直接设置 messages，然后更新 activeConversationId
      setMessages(conv.messages);
      setActiveConversationId(convId);
      setCurrentMode(conv.mode);
    }
  };

  // ================= 删除会话 =================
  const deleteConversation = (convId) => {
    if (conversations.length <= 1) {
      alert('至少保留一个会话！');
      return;
    }

    const newConversations = conversations.filter(c => c.id !== convId);
    setConversations(newConversations);

    // 如果删除的是当前会话，切换到第一个
    if (convId === activeConversationId && newConversations.length > 0) {
      setActiveConversationId(newConversations[0].id);
      setMessages(newConversations[0].messages);
      setCurrentMode(newConversations[0].mode);
    }

    setConversationMenuId(null);
    console.log('✅ 已删除会话:', convId);
  };

  // 选择模式（保留以便后续手动切换）
  const handleModeSelect = (mode) => {
    console.log('✅ 手动切换模式:', mode);
    setCurrentMode(mode);

    if (mode === 'job') {
      // 求职模式：显示上传/填写选择
      setIsResumeModalOpen(true);
    } else {
      // 咨询模式：添加提示消息并加载岗位数据
      const tipMsg = {
        id: generateId(),
        role: 'ai',
        content: '💡 欢迎！我是你的智能就业导师。你可以上传简历让我为你分析，或者直接告诉我你想了解的岗位信息。'
      };
      updateCurrentConversation(prev => [...prev, tipMsg]);
      loadJobList();
    }
  };

  // 加载岗位列表
  const loadJobList = async () => {
    try {
      // 从后端获取岗位数据
      const response = await apiService.getJobList();
      if (response.status === 'success') {
        setJobList(response.data.slice(0, 10)); // 只显示前 10 个
      }
    } catch (error) {
      console.error('加载岗位列表失败:', error);
    }
  };

  // 提交求职意向
  const handleSubmitJobIntention = () => {
    const message = `我想了解以下岗位信息：\n- 学历：${jobIntention.education}\n- 行业：${jobIntention.industry}\n- 意向岗位：${jobIntention.position}`;

    // 添加用户消息
    const userMsg = {
      id: generateId(),
      role: 'user',
      content: message
    };
    updateCurrentConversation(prev => [...prev, userMsg]);

    // 调用后端 API
    sendMessageToBackend(message);
  };

  // 表单提交处理函数
  const handleFormSubmit = () => {
    // 验证必填项
    if (!resumeForm.name || !resumeForm.contact || !resumeForm.intention) {
      alert('请填写必填项（姓名、联系方式、求职意向）');
      return;
    }

    // 将表单数据格式化为简历文本
    const resumeText = `
【基本信息】
姓名：${resumeForm.name}
联系方式：${resumeForm.contact}
求职意向：${resumeForm.intention}
${resumeForm.other ? '其他信息：' + resumeForm.other : ''}

${resumeForm.school ? `【教育经历】\n学校：${resumeForm.school}\n专业与学历：${resumeForm.major}\n就读时间：${resumeForm.schoolTime}\n${resumeForm.schoolInfo ? '补充信息：' + resumeForm.schoolInfo : ''}` : ''}

${resumeForm.company ? `【工作/实习/项目经历】\n公司/项目：${resumeForm.company}\n职位/角色：${resumeForm.role}\n内容描述：\n${resumeForm.description}` : ''}

${resumeForm.skills || resumeForm.certificates ? `【技能与证书】\n${resumeForm.skills ? '专业技能：' + resumeForm.skills : ''}\n${resumeForm.certificates ? '语言与证书：' + resumeForm.certificates : ''}` : ''}

${resumeForm.awards ? `【获奖情况】\n${resumeForm.awards}` : ''}

${resumeForm.selfEval ? `【自我评价】\n${resumeForm.selfEval}` : ''}
    `.trim();

    console.log('📝 表单提交的简历文本:', resumeText);

    // 关闭弹窗
    setIsFormModalOpen(false);

    // 设置模式为求职模式
    setCurrentMode('job');

    // 添加用户消息
    const userMsg = {
      id: generateId(),
      role: 'user',
      content: `我提交了简历信息，求职意向：${resumeForm.intention}`
    };
    updateCurrentConversation(prev => [...prev, userMsg]);

    // 调用求职模式分析接口
    analyzeJobMode(resumeText);
  };

  // 处理粘贴事件
  const handlePaste = async (e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];

      // 检查是否是文件
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) {
          const allowedTypes = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
          ];

          if (allowedTypes.includes(file.type)) {
            e.preventDefault();
            setAttachedFile(file);
            console.log('📎 通过粘贴获取到文件:', file.name, file.type);
            return;
          } else {
            console.log('⚠️ 不支持的文件类型:', file.type);
          }
        }
      }
    }
  };

  // 清理 Markdown 原始标记并优化表格显示
  const cleanMarkdownArtifacts = (text) => {
    if (!text) return '';

    let cleaned = text;

    // 1. 保留完整的 Markdown 表格（有表头和数据行的）
    // 检测是否是表格行：包含 | 符号分隔的内容
    const lines = cleaned.split('\n');
    const processedLines = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // 跳过纯表格分隔符行（如 |---|---|---|）
      if (/^\|\s*[-:|\s]+\|\s*$/.test(line.trim())) {
        continue;
      }

      // 如果是表格内容行（多个 | 分隔的单元格），保留
      // 但清理不完整的表格标记
      if (line.includes('|') && !line.startsWith('|---')) {
        // 清理行首行尾多余的 |
        let processed = line.trim();
        processed = processed.replace(/^\|\s*/, '');  // 移除行首 | 和空格
        processed = processed.replace(/\s*\|$/, '');  // 移除行尾 | 和空格
        // 将 || 替换为 | （清理多余的分隔符）
        processed = processed.replace(/\|\|/g, '|');
        processedLines.push(processed);
      } else {
        processedLines.push(line);
      }
    }

    cleaned = processedLines.join('\n');

    // 2. 清理其他 Markdown  artifacts
    // 清理 <br> 标签（ReactMarkdown 会自动处理换行）
    cleaned = cleaned.replace(/<br>/g, '\n');
    cleaned = cleaned.replace(/<br\s*\/?>/g, '\n');

    return cleaned;
  };

  // 渲染 AI 消息内容（最朴素的 Markdown 渲染）
  const renderAIMessageContent = (content) => {
    if (!content) return '';
      
    // 简单的 Markdown 转 HTML
    const processMarkdown = (text) => {
      let html = text;
      
      // 代码块（先处理）
      html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre style="background:#f5f5f5;padding:8px;overflow-x:auto;font-size:12px;border-radius:4px;"><code>$2</code></pre>');
      
      // 行内代码
      html = html.replace(/`([^`]+)`/g, '<code style="background:#f5f5f5;padding:2px 4px;border-radius:3px;font-size:12px;">$1</code>');
      
      // 先将已转义的 HTML 标签还原（后端可能返回了转义后的 HTML）
      // 第一步：保护已有的 HTML 表格（防止被后续处理破坏）
      const htmlTables = [];
      html = html.replace(/<table[\s\S]*?<\/table>/gi, (match) => {
        const placeholder = `__HTML_TABLE_${htmlTables.length}__`;
        htmlTables.push(match);
        return placeholder;
      });
      
      // 第二步：还原被转义的 HTML 标签
      html = html.replace(/&lt;table([^>]*)(&gt;|>)/gi, '<table$1>').replace(/&lt;\/table(&gt;|>)/gi, '</table>');
      html = html.replace(/&lt;thead([^>]*)(&gt;|>)/gi, '<thead$1>').replace(/&lt;\/thead(&gt;|>)/gi, '</thead>');
      html = html.replace(/&lt;tbody([^>]*)(&gt;|>)/gi, '<tbody$1>').replace(/&lt;\/tbody(&gt;|>)/gi, '</tbody>');
      html = html.replace(/&lt;tr([^>]*)(&gt;|>)/gi, '<tr$1>').replace(/&lt;\/tr(&gt;|>)/gi, '</tr>');
      html = html.replace(/&lt;th([^>]*)(&gt;|>)/gi, '<th$1>').replace(/&lt;\/th(&gt;|>)/gi, '</th>');
      html = html.replace(/&lt;td([^>]*)(&gt;|>)/gi, '<td$1>').replace(/&lt;\/td(&gt;|>)/gi, '</td>');
      html = html.replace(/&lt;br\s*(\/)?(&gt;|>)/gi, '<br/>');
      html = html.replace(/&lt;strong(&gt;|>)/gi, '<strong>').replace(/&lt;\/strong(&gt;|>)/gi, '</strong>');
      html = html.replace(/&lt;em(&gt;|>)/gi, '<em>').replace(/&lt;\/em(&gt;|>)/gi, '</em>');
      html = html.replace(/&lt;li(&gt;|>)/gi, '<li>').replace(/&lt;\/li(&gt;|>)/gi, '</li>');
      html = html.replace(/&lt;ul(&gt;|>)/gi, '<ul>').replace(/&lt;\/ul(&gt;|>)/gi, '</ul>');
      html = html.replace(/&lt;ol(&gt;|>)/gi, '<ol>').replace(/&lt;\/ol(&gt;|>)/gi, '</ol>');
      html = html.replace(/&lt;p(&gt;|>)/gi, '<p>').replace(/&lt;\/p(&gt;|>)/gi, '</p>');
      html = html.replace(/&lt;a([^>]*)(&gt;|>)/gi, '<a$1>').replace(/&lt;\/a(&gt;|>)/gi, '</a>');
      html = html.replace(/&lt;span([^>]*)(&gt;|>)/gi, '<span$1>').replace(/&lt;\/span(&gt;|>)/gi, '</span>');
      html = html.replace(/&lt;h([1-6])([^>]*)(&gt;|>)/gi, '<h$1$2>').replace(/&lt;\/h([1-6])(&gt;|>)/gi, '</h$1>');
      
      // 第三步：再次保护还原后的 HTML 表格
      const htmlTables2 = [];
      html = html.replace(/<table[\s\S]*?<\/table>/gi, (match) => {
        const placeholder = `__HTML_TABLE2_${htmlTables2.length}__`;
        htmlTables2.push(match);
        return placeholder;
      });
      
      // 表格处理（逐行解析 Markdown 表格，在转义HTML之前）
      const lines = html.split('\n');
      let resultLines = [];
      let idx = 0;
      while (idx < lines.length) {
        const line = lines[idx];
        
        // 检测表格开始（以 | 开头的行）
        if (line.trim().startsWith('|') && !line.trim().match(/^\|\s*[-:| ]+\|$/)) {
          // 收集连续的表格行（跳过纯分隔符行）
          let tableRows = [];
          let j = idx;
          
          while (j < lines.length) {
            const currentLine = lines[j].trim();
            // 跳过纯分隔符行
            if (currentLine.match(/^\|\s*[-:| ]+\|$/)) {
              j++;
              continue;
            }
            // 如果是表格内容行（包含 | 且不以 |--- 开头）
            if (currentLine.startsWith('|') && !currentLine.match(/^\|\s*[-:| ]+\|$/)) {
              tableRows.push(currentLine);
              j++;
            } else {
              break;
            }
          }
          
          // 如果收集到至少2行，认为是表格
          if (tableRows.length >= 2) {
            // 第一行作为表头，其余作为数据行
            const headerLine = tableRows[0];
            const dataRows = tableRows.slice(1);
            
            // 解析表头
            const headers = headerLine.split('|')
              .map(h => h.trim())
              .filter(h => h);
            
            // 解析数据行
            const parsedDataRows = dataRows.map(row => 
              row.split('|')
                .map(cell => cell.trim())
                .filter(cell => cell)
            );
            
            // 生成 HTML 表格
            let tableHtml = '<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:12px;border:1px solid #e2e8f0;border-radius:4px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,0.05);">';
            
            // 表头
            tableHtml += '<thead><tr>';
            headers.forEach(h => {
              tableHtml += `<th style="background:#f8fafc;padding:6px 8px;text-align:left;font-weight:600;border-bottom:2px solid #e2e8f0;color:#0f172a;">${h}</th>`;
            });
            tableHtml += '</tr></thead>';
            
            // 表体
            tableHtml += '<tbody>';
            parsedDataRows.forEach((row, ri) => {
              const bg = ri % 2 === 0 ? '#ffffff' : '#fafbfc';
              tableHtml += `<tr style="background:${bg};">`;
              row.forEach(cell => {
                tableHtml += `<td style="padding:6px 8px;border-bottom:1px solid #f1f5f9;color:#334155;line-height:1.4;">${cell}</td>`;
              });
              tableHtml += '</tr>';
            });
            tableHtml += '</tbody></table>';
            
            resultLines.push(tableHtml);
            idx = j;
            continue;
          }
        }
        
        resultLines.push(line);
        idx++;
      }
      html = resultLines.join('\n');
      
      // 第四步：保护 Markdown 转换生成的 HTML 表格（防止被转义）
      const mdTables = [];
      html = html.replace(/<table[\s\S]*?<\/table>/gi, (match) => {
        const placeholder = `__MD_TABLE_${mdTables.length}__`;
        mdTables.push(match);
        return placeholder;
      });
      
      // 第五步：转义 HTML 特殊字符(但不影响已保护的表格占位符)
      html = html.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      
      // 第六步：还原所有 HTML 表格（包括第一步、第三步和第四步保护的）
      htmlTables.forEach((table, i) => {
        html = html.replace(`__HTML_TABLE_${i}__`, table);
      });
      htmlTables2.forEach((table, i) => {
        html = html.replace(`__HTML_TABLE2_${i}__`, table);
      });
      mdTables.forEach((table, i) => {
        html = html.replace(`__MD_TABLE_${i}__`, table);
      });
      
      // 标题
      html = html.replace(/^### (.+)$/gm, '<h3 style="font-size:14px;font-weight:bold;margin:6px 0;">$1</h3>');
      html = html.replace(/^## (.+)$/gm, '<h2 style="font-size:15px;font-weight:bold;margin:8px 0;">$1</h2>');
      html = html.replace(/^# (.+)$/gm, '<h1 style="font-size:16px;font-weight:bold;margin:10px 0;">$1</h1>');
      
      // 粗体和斜体
      html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');
      html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
      
      // 无序列表
      html = html.replace(/^[\s]*[-*] (.+)$/gm, '<li style="margin:2px 0;">$1</li>');
      html = html.replace(/(<li[^>]*>.*<\/li>\n?)+/g, '<ul style="padding-left:18px;margin:4px 0;">$&</ul>');
      
      // 有序列表
      html = html.replace(/^[\s]*\d+\. (.+)$/gm, '<li style="margin:2px 0;">$1</li>');
      
      // 分隔线
      html = html.replace(/^---$/gm, '<hr style="border:none;border-top:1px solid #e0e0e0;margin:8px 0;">');
      
      // 引用块
      html = html.replace(/^> (.+)$/gm, '<blockquote style="border-left:3px solid #3b82f6;background:#f8f9fa;padding:4px 8px;margin:4px 0;">$1</blockquote>');
      
      // 垂直路径箭头优化
      html = html.replace(/路径①/g, '<strong style="color:#2563eb;">路径① →</strong>');
      html = html.replace(/路径②/g, '<strong style="color:#2563eb;">路径② →</strong>');
      html = html.replace(/路径③/g, '<strong style="color:#2563eb;">路径③ →</strong>');
      
      // 换行
      html = html.replace(/\n/g, '<br>');
      
      return html;
    };
      
    return (
      <div 
        style={{ 
          fontSize: '13px',
          lineHeight: '1.4',
          color: '#333',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word'
        }}
        dangerouslySetInnerHTML={{ __html: processMarkdown(content) }}
      />
    );
  };

  // 编辑报告状态
  const [editingMsgId, setEditingMsgId] = useState(null);
  const [editText, setEditText] = useState('');

  // 打开编辑模式
  const handleEditReport = (msgId, content) => {
    setEditingMsgId(msgId);
    setEditText(content);
  };

  // 保存编辑后的报告
  const handleSaveReport = (msgId) => {
    updateCurrentConversation(
      messages.map(msg =>
        msg.id === msgId ? { ...msg, content: editText } : msg
      )
    );
    setEditingMsgId(null);
    setEditText('');
  };

  // 取消编辑
  const handleCancelEdit = () => {
    setEditingMsgId(null);
    setEditText('');
  };

  // 导出报告为 Markdown 文件
  const handleExportReport = (content) => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `职业规划报告_${new Date().toLocaleDateString()}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 导出报告为 TXT 文件
  const handleExportTxt = (content) => {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `职业规划报告_${new Date().toLocaleDateString()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 导出报告为 PDF 文件（使用 html2pdf.js 实现所见即所得）
  const handleExportPDF = (msgId) => {
    try {
      // 找到对应的消息元素
      const originalElement = document.querySelector(`[data-msg-id="${msgId}"]`);
      if (!originalElement) {
        alert('未找到报告内容，请确保消息已完全加载');
        return;
      }

      // 创建克隆容器用于 PDF 导出
      const exportContainer = document.createElement('div');
      exportContainer.style.cssText = `
        position: absolute;
        left: -9999px;
        top: 0;
        width: 800px;
        background: white;
        padding: 30px;
        font-family: 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
        color: #1a1a1a;
        line-height: 1.6;
        font-size: 14px;
      `;

      // 克隆内容
      const clonedContent = originalElement.cloneNode(true);

      // 清理克隆元素，但保留基础样式（关键修复）
      const cleanElement = (el) => {
        // 移除 Tailwind 暗色背景和复杂类名
        const classList = el.getAttribute('class');
        if (classList) {
          el.setAttribute('class', classList.replace(/bg-gray-\d+|text-gray-\d+/g, ''));
        }

        // 移除可能导致问题的样式，但保留颜色、边距等基础样式
        const styleAttr = el.getAttribute('style');
        if (styleAttr) {
          // 替换不支持的 CSS 属性
          let newStyle = styleAttr
            .replace(/oklch\([^)]+\)/g, '#000000')
            .replace(/box-shadow/g, 'box-shadow') // 保留但后续会移除
            .replace(/filter/g, 'filter')
            .replace(/backdrop-filter/g, 'backdrop-filter')
            .replace(/mix-blend-mode/g, 'mix-blend-mode');
          
          // 移除不支持的属性
          el.style.removeProperty('box-shadow');
          el.style.removeProperty('filter');
          el.style.removeProperty('backdrop-filter');
          el.style.removeProperty('mix-blend-mode');
        }

        // 递归处理子元素
        Array.from(el.children).forEach(cleanElement);
      };
      cleanElement(clonedContent);

      // 设置基础样式
      clonedContent.style.cssText = `
        background: white;
        color: #1a1a1a;
        font-size: 14px;
        line-height: 1.8;
        padding: 0;
        margin: 0;
      `;

      // 处理表格样式
      const tables = clonedContent.querySelectorAll('table');
      tables.forEach(table => {
        table.style.cssText = `
          width: 100%;
          border-collapse: collapse;
          margin: 16px 0;
          font-size: 13px;
          page-break-inside: avoid;
        `;

        // 表头
        const ths = table.querySelectorAll('th');
        ths.forEach(th => {
          th.style.cssText = `
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            padding: 10px 12px;
            text-align: left;
            font-weight: 600;
            color: #212529;
            page-break-inside: avoid;
          `;
        });

        // 表格内容
        const tds = table.querySelectorAll('td');
        tds.forEach(td => {
          td.style.cssText = `
            border: 1px solid #dee2e6;
            padding: 10px 12px;
            color: #495057;
            background: white;
            page-break-inside: avoid;
          `;
        });
      });

      // 处理标题
      const headings = clonedContent.querySelectorAll('h1, h2, h3, h4, h5, h6');
      headings.forEach(h => {
        const level = parseInt(h.tagName[1]);
        const sizes = {1: '24px', 2: '20px', 3: '18px', 4: '16px', 5: '14px', 6: '13px'};
        h.style.cssText = `
          font-size: ${sizes[level] || '14px'};
          font-weight: bold;
          margin: 20px 0 12px 0;
          color: #1a1a1a;
          page-break-after: avoid;
        `;
      });

      // 处理列表
      const lists = clonedContent.querySelectorAll('ul, ol');
      lists.forEach(list => {
        list.style.cssText = `
          margin: 12px 0;
          padding-left: 24px;
        `;
      });
      const listItems = clonedContent.querySelectorAll('li');
      listItems.forEach(li => {
        li.style.cssText = `
          margin: 6px 0;
          color: #495057;
        `;
      });

      // 处理段落
      const paragraphs = clonedContent.querySelectorAll('p');
      paragraphs.forEach(p => {
        p.style.cssText = `
          margin: 10px 0;
          color: #495057;
          page-break-inside: avoid;
        `;
      });

      // 处理代码块
      const codeBlocks = clonedContent.querySelectorAll('pre, code');
      codeBlocks.forEach(code => {
        code.style.cssText = `
          background: #f8f9fa;
          border: 1px solid #e9ecef;
          padding: 12px;
          border-radius: 4px;
          font-family: 'Consolas', 'Monaco', monospace;
          font-size: 13px;
          overflow-x: auto;
          page-break-inside: avoid;
        `;
      });

      // 处理分隔线
      const hrs = clonedContent.querySelectorAll('hr');
      hrs.forEach(hr => {
        hr.style.cssText = `
          border: none;
          border-top: 2px solid #e9ecef;
          margin: 20px 0;
        `;
      });

      exportContainer.appendChild(clonedContent);
      document.body.appendChild(exportContainer);

      // 等待 DOM 渲染完成
      setTimeout(() => {
        const opt = {
          margin: [15, 15, 15, 15], // 上右下左边距 (mm)
          filename: `职业规划报告_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.pdf`,
          image: { type: 'jpeg', quality: 0.98 },
          html2canvas: {
            scale: 2,
            useCORS: true,
            backgroundColor: '#ffffff',
            logging: false,
            letterRendering: true,
            width: 800,
            windowWidth: 800
          },
          jsPDF: {
            unit: 'mm',
            format: 'a4',
            orientation: 'portrait'
          },
          pagebreak: { mode: ['avoid-all', 'css', 'legacy'] }
        };

        // 开始导出
        html2pdf().set(opt).from(exportContainer).save().then(() => {
          // 清理临时元素
          document.body.removeChild(exportContainer);
          console.log('✅ PDF 导出成功');
        }).catch(err => {
          console.error('PDF 导出失败:', err);
          document.body.removeChild(exportContainer);
          alert('PDF 导出失败，请尝试使用 Markdown 或 TXT 导出');
        });
      }, 500); // 延迟 500ms 确保 DOM 完全渲染
    } catch (error) {
      console.error('PDF 导出失败:', error);
      alert('PDF 导出失败，请尝试使用 Markdown 或 TXT 导出');
    }
  };

  // 求职模式分析函数
  const analyzeJobMode = async (resumeText) => {
    // 记录请求开始时间
    const requestStartTime = Date.now();

    // 设置 AI 为思考状态
    setIsThinking(true);

    // 记录当前正在流式输出的会话 ID
    const sourceConvId = activeConversationIdRef.current;
    streamingConversationIdRef.current = sourceConvId;

    // 提前声明 reportMsgId，防止 catch 块中引用未定义变量
    let reportMsgId = null;

    try {
      console.log('🎯 开始求职模式分析...');

      // 创建一个空的 AI 消息用于显示报告
      reportMsgId = generateId();
      const reportMsg = {
        id: reportMsgId,
        role: 'ai',
        content: '正在匹配岗位...'
      };
      updateCurrentConversation(prev => [...prev, reportMsg], sourceConvId);

      // 调用求职模式分析接口
      const response = await apiService.analyzeJobMode({
        resume_text: resumeText,
        target_job: '', // 让 AI 自动推荐
        stream: true
      });

      if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedContent = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          console.log('📦 收到报告数据块:', chunk);

          const lines = chunk.split('\n').filter(line => line.trim());

          for (const line of lines) {
            try {
              const data = JSON.parse(line);
              if (data.type === 'report_chunk') {
                accumulatedContent += data.chunk;
                // 使用防抖更新，减少渲染次数
                if (!window._reportUpdateTimer) {
                  window._reportUpdateTimer = setTimeout(() => {
                    updateCurrentConversation(prev =>
                      prev.map(msg =>
                        msg.id === reportMsgId ? { ...msg, content: accumulatedContent } : msg
                      )
                    , sourceConvId);
                    window._reportUpdateTimer = null;
                  }, 50); // 50ms 防抖
                }
              } else if (data.type === 'done') {
                // 计算响应时间
                const responseTime = ((Date.now() - requestStartTime) / 1000).toFixed(2);
                console.log(`⏱️ 响应时间: ${responseTime} 秒`);
                // 确保最后一次更新
                if (window._reportUpdateTimer) {
                  clearTimeout(window._reportUpdateTimer);
                  window._reportUpdateTimer = null;
                }
                updateCurrentConversation(prev =>
                  prev.map(msg =>
                    msg.id === reportMsgId ? { ...msg, content: accumulatedContent, responseTime: parseFloat(responseTime) } : msg
                  )
                , sourceConvId);
                console.log('✅ 报告生成完成，总长度:', accumulatedContent.length);
                setIsThinking(false);
                streamingConversationIdRef.current = null;
              } else if (data.type === 'error') {
                console.error('❌ 报告生成错误:', data.message);
                const errorResponseTime = ((Date.now() - requestStartTime) / 1000).toFixed(2);
                updateCurrentConversation(prev =>
                  prev.map(msg =>
                    msg.id === reportMsgId ? { ...msg, content: `❌ 错误：${data.message}`, responseTime: parseFloat(errorResponseTime) } : msg
                  )
                , sourceConvId);
                setIsThinking(false);
                streamingConversationIdRef.current = null;
              }
            } catch (e) {
              console.error('解析报告失败:', e, '原始数据:', line);
            }
          }
        }
      }
    } catch (error) {
      console.error('求职模式分析失败:', error);
      const failResponseTime = ((Date.now() - requestStartTime) / 1000).toFixed(2);
      // 只有当 reportMsgId 已定义时才更新消息
      if (reportMsgId) {
        updateCurrentConversation(prev =>
          prev.map(msg =>
            msg.id === reportMsgId ? { ...msg, content: `❌ 分析失败：${error.message}`, responseTime: parseFloat(failResponseTime) } : msg
          )
        , sourceConvId);
      }
      streamingConversationIdRef.current = null;
      // 重置思考状态
      setIsThinking(false);
    }
  };

  // 分析用户意图（求职 or 咨询）
  const analyzeUserIntent = (message) => {
    const jobKeywords = [
      '找工作', '求职', '应聘', '投简历', '简历分析', '岗位匹配',
      '职业规划', '就业', '面试', 'offer', '内推', '招聘'
    ];

    const consultKeywords = [
      '了解', '咨询', '问问', '什么岗位', '岗位要求', '薪资',
      '发展前景', '行业', '技能要求', '工作内容', '怎么样'
    ];

    const lowerMsg = message.toLowerCase();

    // 检查是否包含求职关键词
    const hasJobIntent = jobKeywords.some(keyword => lowerMsg.includes(keyword));
    // 检查是否包含咨询关键词
    const hasConsultIntent = consultKeywords.some(keyword => lowerMsg.includes(keyword));

    // 优先判断求职意图（因为求职通常更明确）
    if (hasJobIntent) {
      return 'job';
    } else if (hasConsultIntent) {
      return 'consult';
    }

    // 默认返回 null，让后端处理
    return null;
  };

  // 自动设置模式
  const autoSetMode = (intent) => {
    if (!intent || currentMode === intent) return;

    console.log('🎯 自动识别用户意图:', intent);
    setCurrentMode(intent);

    if (intent === 'consult') {
      // 咨询模式：加载岗位列表
      loadJobList();
    }
  };

  // 发送消息到后端（流式输出）
  const sendMessageToBackend = async (message) => {
    // 记录请求开始时间
    const requestStartTime = Date.now();

    // 设置 AI 为思考状态
    setIsThinking(true);

    // 记录当前正在流式输出的会话 ID
    const sourceConvId = activeConversationIdRef.current;
    streamingConversationIdRef.current = sourceConvId;
    isStreamingRef.current = true;

    // 自动分析用户意图并设置模式
    const detectedIntent = analyzeUserIntent(message);
    autoSetMode(detectedIntent);

    // 先添加用户消息到列表
    const userMsg = {
      id: generateId(),
      role: 'user',
      content: message,
      file: attachedFile ? { name: attachedFile.name, type: attachedFile.type } : null
    };
    updateCurrentConversation(prev => [...prev, userMsg]);

    // 如果有附件，先上传
    if (attachedFile) {
      try {
        console.log('📄 开始上传附件:', attachedFile.name);
        const uploadResult = await apiService.uploadResume(attachedFile);

        if (uploadResult.status === 'success') {
          console.log('✅ 附件上传成功:', uploadResult.file_path);
          setResumeData({
            file_path: uploadResult.file_path,
            resume_text: uploadResult.resume_text,
            file_name: uploadResult.file_name
          });

          // 添加系统消息
          const sysMsg = {
            id: generateId(),
            role: 'ai',
            content: `✅ 简历已上传并解析成功！

**文件名**: ${uploadResult.file_name}
**解析内容**: ${uploadResult.resume_text.substring(0, 200)}...

接下来我将为你进行岗位匹配分析...`
          };
          updateCurrentConversation(prev => [...prev, sysMsg]);

          // 清空附件
          setAttachedFile(null);

          // 自动调用求职模式分析接口
          analyzeJobMode(uploadResult.resume_text);
          return;
        }
      } catch (error) {
        console.error('❌ 上传失败:', error);
        const errorMsg = {
          id: generateId(),
          role: 'ai',
          content: `❌ 简历上传失败：${error.message}`
        };
        updateCurrentConversation(prev => [...prev, errorMsg]);
        setAttachedFile(null);
        return;
      }
    }

    // 创建一个空的 AI 消息用于流式显示
    const aiMsgId = generateId();
    const aiMsg = {
      id: aiMsgId,
      role: 'ai',
      content: '💭 思考中...',
      responseTime: null // 记录响应时间
    };
    // 注意：这里使用 sourceConvId 确保消息添加到正确的会话
    updateCurrentConversation(prev => [...prev, aiMsg], sourceConvId);

    try {
      console.log('📡 开始发送请求到后端...');

      // 调用后端 API（流式模式）
      const response = await apiService.chat({
        message,
        conversation_history: messages.slice(-5),
        mode: currentMode,
        resume: resumeData,
        job_intention: jobIntention,
        stream: true
      });

      console.log('📥 收到响应:', response);

      // 处理流式响应（支持 LangGraph astream_events）
      if (response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedContent = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);

          // 解析 NDJSON 格式的响应
          const lines = chunk.split('\n').filter(line => line.trim());

          for (const line of lines) {
            try {
              const data = JSON.parse(line);

              switch (data.type) {
                case 'status':
                  // 显示进度状态
                  updateCurrentConversation(prev =>
                    prev.map(msg =>
                      msg.id === aiMsgId ? { ...msg, content: data.message } : msg
                    )
                  , sourceConvId);
                  break;

                case 'chunk':
                case 'report_chunk':
                  // 累加报告内容（真正的流式 token）
                  accumulatedContent += data.chunk || data.content;
                  updateCurrentConversation(prev =>
                    prev.map(msg =>
                      msg.id === aiMsgId ? { ...msg, content: accumulatedContent } : msg
                    )
                  , sourceConvId);
                  break;

                case 'match_result':
                  console.log('📊 收到匹配结果:', data.data);
                  break;

                case 'parsed_profile':
                  console.log('👤 收到用户画像:', data.data);
                  break;

                case 'transfer_paths':
                  console.log('🛤️ 收到换岗路径:', data.data);
                  break;

                case 'done':
                  console.log('✅ 流式输出完成');
                  // 计算响应时间
                  const responseTime = ((Date.now() - requestStartTime) / 1000).toFixed(2);
                  console.log(`⏱️ 响应时间: ${responseTime} 秒`);
                  // 更新消息添加响应时间
                  updateCurrentConversation(prev =>
                    prev.map(msg =>
                      msg.id === aiMsgId ? { ...msg, responseTime: parseFloat(responseTime) } : msg
                    )
                  , sourceConvId);
                  streamingConversationIdRef.current = null;
                  isStreamingRef.current = false;
                  break;

                case 'error':
                  console.error('❌ 流式输出错误:', data.message);
                  // 即使出错也记录时间
                  const errorResponseTime = ((Date.now() - requestStartTime) / 1000).toFixed(2);
                  updateCurrentConversation(prev =>
                    prev.map(msg =>
                      msg.id === aiMsgId ? { ...msg, content: `❌ 错误：${data.message}`, responseTime: parseFloat(errorResponseTime) } : msg
                    )
                  , sourceConvId);
                  streamingConversationIdRef.current = null;
                  isStreamingRef.current = false;
                  break;

                default:
                  console.log('⚠️ 未知事件类型:', data.type);
              }
            } catch (e) {
              console.error('解析响应失败:', e, '原始数据:', line);
            }
          }
        }
      } else {
        // 如果没有 body，说明是普通响应
        console.log('⚠️ 非流式响应，直接使用返回数据');
        const normalResponseTime = ((Date.now() - requestStartTime) / 1000).toFixed(2);
        if (response.status === 'success') {
          updateCurrentConversation(prev =>
            prev.map(msg =>
              msg.id === aiMsgId ? { ...msg, content: response.reply, responseTime: parseFloat(normalResponseTime) } : msg
            )
          );
        }
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      // 即使出错也记录时间
      const failResponseTime = ((Date.now() - requestStartTime) / 1000).toFixed(2);
      // 显示错误消息
      updateCurrentConversation(prev =>
        prev.map(msg =>
          msg.id === aiMsgId ? { ...msg, content: `❌ 请求失败：${error.message}`, responseTime: parseFloat(failResponseTime) } : msg
        )
      , sourceConvId);
      streamingConversationIdRef.current = null;
      isStreamingRef.current = false;
      setIsThinking(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-white text-gray-800 overflow-hidden relative">

      {/* ================= 左侧边栏 ================= */}
      <div className="hidden md:flex flex-col w-64 bg-gray-50 border-r border-gray-200">
        <div className="p-4">
          <button
            onClick={handleNewChat}
            className="flex items-center justify-center w-full gap-2 py-2.5 bg-white border border-gray-300 rounded-full hover:bg-gray-100 transition shadow-sm text-sm font-medium"
          >
            <span className="text-lg">+</span> 发起新对话
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-1" onClick={() => setConversationMenuId(null)}>
          <p className="text-xs text-gray-500 font-semibold px-2 mb-2">近期对话</p>
          {conversations.map((conv) => (
            <div key={conv.id} className="relative group" onClick={(e) => e.stopPropagation()}>
              <button
                onClick={() => switchToConversation(conv.id)}
                className={`w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-gray-200 truncate transition ${
                  activeConversationId === conv.id ? 'bg-gray-200 font-medium' : ''
                }`}
              >
                {conv.name || '新的对话'}
              </button>
              {/* 三点菜单 */}
              <div className="absolute right-1 top-1/2 -translate-y-1/2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setConversationMenuId(conversationMenuId === conv.id ? null : conv.id);
                  }}
                  className="p-1 rounded hover:bg-gray-300 opacity-0 group-hover:opacity-100 transition"
                >
                  <svg className="w-4 h-4 text-gray-500" viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="5" r="2" />
                    <circle cx="12" cy="12" r="2" />
                    <circle cx="12" cy="19" r="2" />
                  </svg>
                </button>
                {/* 弹出菜单 */}
                {conversationMenuId === conv.id && (
                  <div className="absolute right-0 top-8 w-32 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50" onClick={(e) => e.stopPropagation()}>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteConversation(conv.id);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition flex items-center gap-2"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      删除
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        <div className="p-4 border-t border-gray-200">
          <button className="flex items-center gap-2 text-sm hover:text-gray-600">
            <span className="text-xl">⚙️</span> 设置和帮助
          </button>
        </div>
      </div>

      {/* ================= 右侧主区域 ================= */}
      <div className="flex-1 flex flex-col bg-white overflow-hidden">

        {/* 顶部导航栏 */}
        <header className="h-14 flex items-center justify-between px-4 border-b border-gray-100">
          <button className="md:hidden p-2 text-gray-600">☰</button>
          <div className="flex items-center gap-3 mx-auto md:mx-0">
            <h1 className="text-lg font-medium text-gray-700">智能就业导航</h1>
            {currentMode && (
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                currentMode === 'job' 
                  ? 'bg-blue-100 text-blue-700' 
                  : 'bg-purple-100 text-purple-700'
              }`}>
                {currentMode === 'job' ? '🎯 求职模式' : '💬 咨询模式'}
              </span>
            )}
          </div>
          <div className="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center">U</div>
        </header>

        {/* 聊天记录区 */}
        <div ref={chatContainerRef} className="flex-1 overflow-y-auto p-4 md:p-8 min-h-0">
          <div className="max-w-3xl mx-auto space-y-6">

            {/* 咨询模式的岗位展示 */}
            {currentMode === 'consult' && jobList.length > 0 && (
              <div className="bg-purple-50 rounded-2xl p-6 mb-6 border border-purple-100">
                <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                  <span>💼</span> 热门岗位推荐
                </h3>
                <div className="grid gap-3">
                  {jobList.map((job, index) => (
                    <div key={index} className="bg-white rounded-xl p-4 hover:shadow-md transition cursor-pointer">
                      <div className="flex justify-between items-start mb-2">
                        <h4 className="font-semibold text-gray-800">{job.job_name}</h4>
                        <span className="text-sm text-purple-600 font-medium">{job.salary_range || '面议'}</span>
                      </div>
                      <div className="flex flex-wrap gap-2 mb-2">
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">{job.education}</span>
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">{job.experience}</span>
                        <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">{job.city}</span>
                      </div>
                      <p className="text-sm text-gray-600 line-clamp-2">{job.skills_required}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 渲染消息内容 */}
            {messages && messages.length > 0 && messages.map((msg) => (
              msg.role === 'ai' ? (
                <div key={msg.id} className="flex gap-4 group" data-msg-id={msg.id}>
                  {/* AI 头像 - 思考时添加微光旋转动画 */}
                  <div className={`w-10 h-10 rounded-full overflow-hidden shrink-0 border border-gray-200 relative ${
                    isThinking && (msg.content?.includes('正在匹配岗位') || msg.content?.includes('思考中'))
                      ? 'ring-2 ring-sky-400 ring-offset-2'
                      : ''
                  }`}>
                    {/* 头像图片 */}
                    <img 
                      src={AI_AVATAR_URL} 
                      alt="AI" 
                      className="w-full h-full object-cover scale-150"
                    />
                    {/* 微光旋转环 - 淡蓝色 */}
                    {isThinking && (msg.content?.includes('正在匹配岗位') || msg.content?.includes('思考中')) && (
                      <div className="absolute inset-0 rounded-full border-2 border-sky-400 animate-spin" style={{
                        animationDuration: '1.5s',
                        borderTopColor: 'transparent',
                        borderRightColor: 'transparent',
                      }} />
                    )}
                    {/* 呼吸光晕 - 淡蓝色 */}
                    {isThinking && (msg.content?.includes('正在匹配岗位') || msg.content?.includes('思考中')) && (
                      <div className="absolute inset-0 rounded-full bg-sky-400 animate-pulse opacity-30" />
                    )}
                  </div>
                  <div className="flex-1 pt-1 overflow-hidden">
                    {/* 如果是正在编辑的消息，显示文本框 */}
                    {editingMsgId === msg.id ? (
                      <div className="space-y-2">
                        <textarea
                          value={editText}
                          onChange={(e) => setEditText(e.target.value)}
                          className="w-full border border-gray-300 rounded-lg p-3 text-sm leading-relaxed focus:ring-2 focus:ring-blue-500 outline-none resize-y min-h-[200px]"
                          style={{ fontFamily: 'monospace' }}
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleSaveReport(msg.id)}
                            className="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition"
                          >
                            💾 保存
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="px-4 py-1.5 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300 transition"
                          >
                            ❌ 取消
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        {/* 报告内容容器 */}
                        <div 
                          className="text-gray-800 text-sm whitespace-pre-wrap break-words p-3"
                          style={{ 
                            backgroundColor: '#ffffff',
                            pageBreakInside: 'avoid',
                            breakInside: 'avoid'
                          }}>
                          {renderAIMessageContent(msg.content)}
                        </div>
                        {/* 操作按钮（鼠标悬停时显示） */}
                        <div className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-between">
                          <div className="flex gap-2 flex-wrap">
                            <button
                              onClick={() => handleEditReport(msg.id, msg.content)}
                              className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded hover:bg-gray-200 transition"
                            >
                              ✏️ 编辑
                            </button>
                            <button
                              onClick={() => handleExportReport(msg.content)}
                              className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition"
                            >
                              📄 MD
                            </button>
                            <button
                              onClick={() => handleExportTxt(msg.content)}
                              className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition"
                            >
                              📝 TXT
                            </button>
                            <button
                              onClick={() => handleExportPDF(msg.id)}
                              className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition"
                            >
                              📕 PDF
                            </button>
                          </div>
                          {/* 响应时间统计 */}
                          {msg.responseTime && (
                            <span className="text-xs text-gray-400 bg-gray-50 px-2 py-1 rounded">
                              ⏱️ 响应时间: {msg.responseTime}s
                            </span>
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ) : (
                // 用户气泡渲染 (靠右，无头像)
                <div key={msg.id} className="flex flex-row-reverse">
                  <div className="pt-1 max-w-full">
                    {/* 如果有文件附件，显示文件卡片 */}
                    {msg.file && (
                      <div className="flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 mb-2">
                        <div className="text-red-500">
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                          </svg>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-blue-900 truncate">{msg.file.name}</p>
                          <p className="text-xs text-blue-600">PDF 文件</p>
                        </div>
                      </div>
                    )}
                    {/* 显示消息内容 */}
                    {msg.content && (
                      <div className="bg-blue-50 text-blue-900 px-4 py-2 rounded-2xl rounded-tr-none inline-block">
                        {msg.content}
                      </div>
                    )}
                  </div>
                </div>
              )
            ))}

          </div>
        </div>

        {/* ================= 底部输入框区域 ================= */}
        <div className="bg-gradient-to-t from-white via-white to-transparent pt-6 pb-6 px-4 flex-shrink-0">
          <div className="max-w-3xl mx-auto bg-white rounded-3xl p-3 shadow-lg border border-gray-200 relative">

            {/* 附件预览区域（在输入框内部顶部） */}
            {attachedFile && (
              <div className="flex items-center gap-2 bg-blue-50 px-3 py-2 rounded-lg border border-blue-200 mb-2 animate-fade-in">
                <div className="text-blue-600 shrink-0">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-blue-900 truncate">{attachedFile.name}</p>
                  <p className="text-xs text-blue-600">{(attachedFile.size / 1024).toFixed(1)} KB</p>
                </div>
                <button
                  onClick={() => setAttachedFile(null)}
                  className="text-blue-400 hover:text-blue-600 transition shrink-0"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}

            {/* 输入框和按钮区域 */}
            <div className="flex items-end gap-2">
              {/* "+" 按钮及弹出菜单容器 */}
              <div className="relative shrink-0">
                <button
                  onClick={() => setIsMenuOpen(!isMenuOpen)}
                  className="p-2 text-gray-500 hover:text-gray-700 rounded-full hover:bg-gray-100 transition"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                </button>

                {/* 弹出菜单 */}
                {isMenuOpen && (
                  <div className="absolute bottom-12 left-0 mb-2 w-48 bg-white border border-gray-200 rounded-xl shadow-lg py-2 z-50">
                    <button
                      className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-3 transition"
                      onClick={() => {
                        setIsMenuOpen(false);
                        // 触发文件选择
                        const input = document.createElement('input');
                        input.type = 'file';
                        input.accept = '.pdf,.doc,.docx';
                        input.onchange = (e) => {
                          const file = e.target.files[0];
                          if (file) {
                            setAttachedFile(file);
                          }
                        };
                        input.click();
                      }}
                    >
                      <span>📎</span> 上传简历附件
                    </button>
                    <button
                      className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-3 transition"
                      onClick={() => {
                        setIsMenuOpen(false);
                        setIsFormModalOpen(true);
                      }}
                    >
                      <span>📝</span> 填写简历信息
                    </button>
                  </div>
                )}
              </div>

              <button className="p-2 text-gray-500 hover:text-gray-700 rounded-full hover:bg-gray-100 transition hidden sm:block">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
              </button>

              <textarea
                className="flex-1 bg-transparent border-none focus:ring-0 resize-none py-3 px-2 max-h-32 min-h-[44px] outline-none text-gray-700"
                placeholder={currentMode === 'job' ? "输入你的问题，或上传/填写简历..." : "描述你的求职意向，如学历、行业偏好..."}
                rows={1}
                onPaste={handlePaste}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    const message = e.target.value.trim();
                    if (message) {
                      sendMessageToBackend(message);
                      e.target.value = '';
                    }
                  }
                }}
              />

              <button
                onClick={() => {
                  const textarea = document.querySelector('textarea');
                  const message = textarea.value.trim();
                  if (message) {
                    sendMessageToBackend(message);
                    textarea.value = '';
                  }
                }}
                className="p-2 m-1 bg-black text-white rounded-full hover:bg-gray-800 transition flex items-center justify-center w-10 h-10 shrink-0"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" /></svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ================= 填写简历信息弹窗 (Modal) ================= */}
      {isFormModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4 sm:p-6">
          <div className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col shadow-2xl">

            {/* 弹窗头部 */}
            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50 rounded-t-2xl">
              <div>
                <h2 className="text-xl font-bold text-gray-800">填写简历信息</h2>
                <p className="text-sm text-gray-500 mt-1">请尽量详细填写，这将帮助大模型更精准地生成你的就业能力画像。</p>
              </div>
              <button
                onClick={() => setIsFormModalOpen(false)}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-200 transition"
              >
                ✕
              </button>
            </div>

            {/* 弹窗表单内容 (可滚动区域) */}
            <div className="p-6 overflow-y-auto flex-1 space-y-8 custom-scrollbar">

              {/* 1. 基本信息 */}
              <section>
                <h3 className="text-lg font-semibold text-gray-800 border-l-4 border-blue-500 pl-3 mb-4">基本信息</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">姓名 <span className="text-red-500">*</span></label>
                    <input type="text" placeholder="使用真实姓名" value={resumeForm.name} onChange={(e) => setResumeForm({...resumeForm, name: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">联系方式 <span className="text-red-500">*</span></label>
                    <input type="text" placeholder="手机号码 / 常用电子邮箱" value={resumeForm.contact} onChange={(e) => setResumeForm({...resumeForm, contact: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">求职意向 <span className="text-red-500">*</span></label>
                    <input type="text" placeholder="如：市场营销专员、Java开发工程师" value={resumeForm.intention} onChange={(e) => setResumeForm({...resumeForm, intention: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">其他信息 (可选)</label>
                    <input type="text" placeholder="性别 / 年龄 / 现居城市等" value={resumeForm.other} onChange={(e) => setResumeForm({...resumeForm, other: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                  </div>
                </div>
              </section>

              {/* 2. 教育经历 */}
              <section>
                <h3 className="text-lg font-semibold text-gray-800 border-l-4 border-blue-500 pl-3 mb-4">📚 教育经历</h3>
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">学校名称</label>
                      <input type="text" placeholder="填写全称" value={resumeForm.school} onChange={(e) => setResumeForm({...resumeForm, school: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">专业与学历</label>
                      <input type="text" placeholder="如：计算机科学与技术 (本科)" value={resumeForm.major} onChange={(e) => setResumeForm({...resumeForm, major: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">就读时间</label>
                      <input type="text" placeholder="如：2020.09 - 2024.06" value={resumeForm.schoolTime} onChange={(e) => setResumeForm({...resumeForm, schoolTime: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">补充信息 (可选)</label>
                      <input type="text" placeholder="GPA / 专业排名 / 核心课程" value={resumeForm.schoolInfo} onChange={(e) => setResumeForm({...resumeForm, schoolInfo: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                    </div>
                  </div>
                </div>
              </section>

              {/* 3. 工作/实习/项目经历 */}
              <section>
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-800 border-l-4 border-blue-500 pl-3">💼 工作/实习/项目经历</h3>
                </div>
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-100 space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">公司/项目名称</label>
                      <input type="text" value={resumeForm.company} onChange={(e) => setResumeForm({...resumeForm, company: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">职位/角色 & 时间</label>
                      <input type="text" placeholder="如：前端实习生 | 2023.06-2023.09" value={resumeForm.role} onChange={(e) => setResumeForm({...resumeForm, role: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">内容描述 (建议使用 STAR 原则)</label>
                    <p className="text-xs text-gray-500 mb-2">情境(S)、任务(T)、行动(A)、结果(R)，请尽量包含量化数据。</p>
                    <textarea
                      rows={4}
                      placeholder="- 背景与任务：&#10;- 采取行动：&#10;- 量化成果：效率提升20%..."
                      value={resumeForm.description}
                      onChange={(e) => setResumeForm({...resumeForm, description: e.target.value})}
                      className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-y"
                    />
                  </div>
                </div>
              </section>

              {/* 4. 技能与证书 */}
              <section>
                <h3 className="text-lg font-semibold text-gray-800 border-l-4 border-blue-500 pl-3 mb-4">🛠️ 技能与证书</h3>
                <div className="grid grid-cols-1 gap-4">
                  <textarea rows={2} placeholder="专业技能：如 Java, Python, Figma, Excel..." value={resumeForm.skills} onChange={(e) => setResumeForm({...resumeForm, skills: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none" />
                  <textarea rows={2} placeholder="语言与证书：CET-6 (550分), 注册会计师..." value={resumeForm.certificates} onChange={(e) => setResumeForm({...resumeForm, certificates: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
              </section>

              {/* 5. 获奖情况 & 6. 自我评价 */}
              <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 border-l-4 border-blue-500 pl-3 mb-4">🏆 获奖情况 (可选)</h3>
                  <textarea rows={4} placeholder="全称，颁奖单位，获奖年月，比例等。&#10;如：全国大学生数学建模竞赛 省级一等奖 (前5%)" value={resumeForm.awards} onChange={(e) => setResumeForm({...resumeForm, awards: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-800 border-l-4 border-blue-500 pl-3 mb-4">✨ 自我评价 (可选)</h3>
                  <textarea rows={4} placeholder="概括核心优势、工作态度或职业规划。避免空洞套话。" value={resumeForm.selfEval} onChange={(e) => setResumeForm({...resumeForm, selfEval: e.target.value})} className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none" />
                </div>
              </section>

            </div>

            {/* 弹窗底部按钮 */}
            <div className="px-6 py-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 rounded-b-2xl">
              <button
                onClick={() => setIsFormModalOpen(false)}
                className="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition"
              >
                取消
              </button>
              <button
                onClick={handleFormSubmit}
                className="px-5 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition flex items-center gap-2"
              >
                <span>✨</span> 提交并生成画像
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ================= 简历选择弹窗（求职模式） ================= */}
      {isResumeModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden">
            {/* 弹窗头部 */}
            <div className="px-6 py-4 border-b border-gray-100 bg-gradient-to-r from-blue-50 to-purple-50">
              <div className="flex justify-between items-center">
                <div>
                  <h2 className="text-2xl font-bold text-gray-800">🎯 求职模式</h2>
                  <p className="text-sm text-gray-600 mt-1">请选择简历提交方式</p>
                </div>
                <button
                  onClick={() => setIsResumeModalOpen(false)}
                  className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-white transition"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* 弹窗内容 */}
            <div className="p-8">
              <div className="grid md:grid-cols-2 gap-6">
                {/* 上传简历附件 */}
                <div
                  onClick={() => {
                    setIsResumeModalOpen(false);
                    // 触发文件上传
                    const input = document.createElement('input');
                    input.type = 'file';
                    input.accept = '.pdf,.doc,.docx';
                    input.onchange = async (e) => {
                      const file = e.target.files[0];
                      if (file) {
                        console.log('📄 选择的文件:', file);
                        // TODO: 调用上传接口
                        alert(`已选择文件：${file.name}\n接下来将解析简历并生成画像...`);
                      }
                    };
                    input.click();
                  }}
                  className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-2xl p-6 cursor-pointer hover:shadow-lg hover:scale-105 transition-all border-2 border-blue-200 hover:border-blue-400 group"
                >
                  <div className="text-5xl mb-4 group-hover:scale-110 transition-transform">📎</div>
                  <h3 className="text-xl font-bold text-gray-800 mb-2">上传简历附件</h3>
                  <p className="text-sm text-gray-600 mb-4">支持 PDF、DOC、DOCX 格式</p>
                  <ul className="space-y-1 text-xs text-gray-500">
                    <li className="flex items-start gap-1">
                      <span className="text-blue-500 mt-0.5">✓</span>
                      <span>快速上传，自动解析</span>
                    </li>
                    <li className="flex items-start gap-1">
                      <span className="text-blue-500 mt-0.5">✓</span>
                      <span>智能提取关键信息</span>
                    </li>
                    <li className="flex items-start gap-1">
                      <span className="text-blue-500 mt-0.5">✓</span>
                      <span>生成精准岗位匹配</span>
                    </li>
                  </ul>
                  <button className="mt-4 w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition">
                    选择文件
                  </button>
                </div>

                {/* 填写简历信息 */}
                <div
                  onClick={() => {
                    setIsResumeModalOpen(false);
                    setIsFormModalOpen(true);
                  }}
                  className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-2xl p-6 cursor-pointer hover:shadow-lg hover:scale-105 transition-all border-2 border-purple-200 hover:border-purple-400 group"
                >
                  <div className="text-5xl mb-4 group-hover:scale-110 transition-transform">📝</div>
                  <h3 className="text-xl font-bold text-gray-800 mb-2">填写简历信息</h3>
                  <p className="text-sm text-gray-600 mb-4">在线编辑，灵活定制</p>
                  <ul className="space-y-1 text-xs text-gray-500">
                    <li className="flex items-start gap-1">
                      <span className="text-purple-500 mt-0.5">✓</span>
                      <span>结构化信息填写</span>
                    </li>
                    <li className="flex items-start gap-1">
                      <span className="text-purple-500 mt-0.5">✓</span>
                      <span>突出个人优势</span>
                    </li>
                    <li className="flex items-start gap-1">
                      <span className="text-purple-500 mt-0.5">✓</span>
                      <span>定制化职业画像</span>
                    </li>
                  </ul>
                  <button className="mt-4 w-full py-2.5 bg-purple-600 text-white rounded-lg font-medium hover:bg-purple-700 transition">
                    开始填写
                  </button>
                </div>
              </div>

              {/* 提示信息 */}
              <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <span className="font-semibold">💡 温馨提示：</span>
                  两种方式均可生成完整的就业能力画像，包括岗位匹配度分析、职业发展路径规划等。
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default ChatInterface;