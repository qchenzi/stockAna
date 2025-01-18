Page({
  data: {
    stockCode: '',
    analysis: null,
    formattedAnalysis: '',
    suggestions: [],
    analysisDate: '',
    date: '',
    showDatePicker: false,
    currentDate: new Date().getTime(),
    minDate: new Date().setDate(new Date().getDate() - 7),
    maxDate: new Date().getTime(),
    stockName: ''
  },

  onLoad() {
    const today = new Date();
    const dayOfWeek = today.getDay();
    
    if (dayOfWeek === 0) {
      today.setDate(today.getDate() - 2);
    } else if (dayOfWeek === 6) {
      today.setDate(today.getDate() - 1);
    }
    
    const dateStr = today.toISOString().split('T')[0];
    
    this.setData({ 
      date: dateStr,
      currentDate: today.getTime(),
      minDate: new Date().setDate(new Date().getDate() - 7),
      maxDate: new Date().getTime()
    });
  },

  onShowDatePicker() {
    if (!this.data.stockCode) {
      wx.showToast({
        title: '请先选择股票',
        icon: 'none'
      });
      return;
    }
    this.setData({ 
      showDatePicker: true,
      currentDate: this.data.date ? new Date(this.data.date).getTime() : new Date().getTime()
    });
  },

  onCloseDatePicker() {
    this.setData({ showDatePicker: false });
  },

  onDateConfirm(event) {
    const date = new Date(event.detail);
    const dayOfWeek = date.getDay();
    
    if (dayOfWeek === 0 || dayOfWeek === 6) {
      wx.showToast({
        title: '请选择工作日',
        icon: 'none'
      });
      return;
    }

    const oneWeekAgo = new Date();
    oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
    oneWeekAgo.setHours(0, 0, 0, 0);
    
    if (date < oneWeekAgo) {
      wx.showToast({
        title: '仅支持最近7天分析',
        icon: 'none'
      });
      return;
    }
    
    const dateStr = date.toISOString().split('T')[0];
    this.setData({
      date: dateStr,
      currentDate: date.getTime(),
      showDatePicker: false
    });

    if (this.data.stockCode) {
      this.onAnalyze();
    }
  },

  onStockCodeInput(event) {
    const code = event.detail;
    this.setData({ stockCode: code });
    
    if (code.length >= 2) {
      this.searchStocks(code);
    } else {
      this.setData({ suggestions: [] });
    }
  },

  async searchStocks(keyword) {
    try {
      const res = await new Promise((resolve, reject) => {
        wx.request({
          url: `${getApp().globalData.baseUrl}/api/stocks/search`,
          data: { keyword },
          success: resolve,
          fail: reject
        });
      });

      if (res.statusCode === 200 && res.data) {
        this.setData({
          suggestions: res.data
        });
      }
    } catch (error) {
      console.error('搜索股票失败:', error);
    }
  },

  onSelectStock(event) {
    const { code, name } = event.currentTarget.dataset.stock;
    this.setData({
      stockCode: code,
      stockName: name,
      suggestions: []
    });
  },

  async onAnalyze() {
    if (!this.data.stockCode) {
      wx.showToast({
        title: '请输入股票代码',
        icon: 'none'
      });
      return;
    }

    try {
      wx.showLoading({ title: 'AI分析中,请等待...' });
      
      const res = await new Promise((resolve, reject) => {
        wx.request({
          url: `${getApp().globalData.baseUrl}/api/ai/analysis/${this.data.stockCode}`,
          method: 'GET',
          data: { date: this.data.date },
          success: resolve,
          fail: reject
        });
      });

      if (res.statusCode === 200 && res.data) {
        const formattedAnalysis = this.formatAnalysisData(res.data.analysis);
        this.setData({
          analysis: formattedAnalysis,
          analysisDate: this.data.date
        });
      } else {
        wx.showToast({
          title: res.data?.error || '分析失败',
          icon: 'none'
        });
      }
    } catch (error) {
      console.error('AI分析请求失败:', error);
      wx.showToast({
        title: '网络请求失败',
        icon: 'none'
      });
    } finally {
      wx.hideLoading();
    }
  },

  formatAnalysisData(data) {
    try {
      const analysis = typeof data === 'string' ? JSON.parse(data) : data;
      
      // 基础结构
      const formatted = {
        趋势判断: analysis.趋势判断 || '未知',
        交易信号: analysis.交易信号 || '未知',
        分析依据: {},
        风险评估: {},
        收益分析: {},
        执行建议: {}
      };

      // 通用处理函数：递归处理对象或字符串
      const processSection = (section) => {
        if (!section) return {};
        
        // 如果是字符串，尝试解析为对象
        if (typeof section === 'string') {
          try {
            return JSON.parse(section);
          } catch {
            // 如果不是JSON字符串，按段落拆分
            const paragraphs = section.split('\n').filter(p => p.trim());
            return { content: paragraphs.join('\n') };
          }
        }
        
        // 如果是对象，直接返回
        if (typeof section === 'object') {
          return section;
        }
        
        return {};
      };

      // 处理各个部分
      if (analysis.分析依据) {
        formatted.分析依据 = processSection(analysis.分析依据);
      }

      if (analysis.风险评估) {
        formatted.风险评估 = processSection(analysis.风险评估);
      }

      if (analysis.收益分析) {
        formatted.收益分析 = processSection(analysis.收益分析);
      }

      if (analysis.执行建议) {
        formatted.执行建议 = processSection(analysis.执行建议);
      }

      return formatted;
    } catch (error) {
      console.error('格式化分析数据失败:', error);
      return {
        趋势判断: '解析失败',
        交易信号: '解析失败',
        分析依据: {},
        风险评估: {},
        收益分析: {},
        执行建议: {}
      };
    }
  }
}); 