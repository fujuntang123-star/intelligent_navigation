// API 服务配置
const API_BASE_URL = ''; // 使用 Vite 代理

// 通用请求处理
async function handleRequest(url, options = {}) {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  };

  try {
    const response = await fetch(`${API_BASE_URL}${url}`, defaultOptions);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API 请求失败:', error);
    throw error;
  }
}

// API 服务
export const apiService = {
  // 获取岗位列表（咨询模式使用）
  getJobList() {
    return handleRequest('/api/job_list');
  },
  
  // 普通聊天（流式输出）
  async chat(data) {
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
      },
      method: 'POST',
      body: JSON.stringify(data),
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, defaultOptions);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      // 直接返回 response，让调用者处理流式数据
      return response;
    } catch (error) {
      console.error('API 请求失败:', error);
      throw error;
    }
  },
  
  // 求职模式：分析简历并生成职业规划（流式）
  async analyzeJobMode(data) {
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
      },
      method: 'POST',
      body: JSON.stringify(data),
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/job_mode/analyze`, defaultOptions);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return response;
    } catch (error) {
      console.error('求职模式分析失败:', error);
      throw error;
    }
  },
  
  // 咨询模式：选择岗位并咨询（流式）
  async selectConsultJob(data) {
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
      },
      method: 'POST',
      body: JSON.stringify(data),
    };

    try {
      const response = await fetch(`${API_BASE_URL}/api/consult_mode/select_job`, defaultOptions);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return response;
    } catch (error) {
      console.error('咨询模式选择失败:', error);
      throw error;
    }
  },
  
  // 上传简历
  async uploadResume(file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/upload-resume`, {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error('上传简历失败:', error);
      throw error;
    }
  },
  
  // 1. 获取职业规划信息
  getJobCareerPlanning(jobName) {
    return handleRequest(`/api/job_career_planning/${encodeURIComponent(jobName)}`);
  },

  // 2. 获取换岗路径
  getJobTransferPaths(jobName) {
    return handleRequest(`/api/job_transfer_paths/${encodeURIComponent(jobName)}`);
  },

  // 3. 分析简历并生成报告
  analyzeResume(resumeText, targetJob) {
    return handleRequest('/api/analyze', {
      method: 'POST',
      body: JSON.stringify({
        resume: resumeText,
        target_job: targetJob,
      }),
    });
  },

  // 4. 导出 Markdown 报告
  exportMarkdown(reportData) {
    return handleRequest('/api/export_report/markdown', {
      method: 'POST',
      body: JSON.stringify(reportData),
    });
  },

  // 5. 智能润色
  polishReport(content, contextType = 'report') {
    return handleRequest('/api/polish_report', {
      method: 'POST',
      body: JSON.stringify({
        content,
        context_type: contextType,
      }),
    });
  },

  // 6. 完整性检查
  checkIntegrity(content, requiredSections = []) {
    return handleRequest('/api/check_integrity', {
      method: 'POST',
      body: JSON.stringify({
        content,
        required_sections: requiredSections,
      }),
    });
  },
};

export default apiService;
