Page({
  data: {
    stockCode: '',
    stockName: '',
    suggestions: [],
    analysis: null,
    analysisDate: '',
    parsedAnalysis: null,
    loading: false
  },

  onLoad(options) {
    // 处理从其他页面传入的参数
    if (options.code) {
      this.setData({ 
        stockCode: options.code 
      });
      // 自动开始分析
      this.onAnalyze();
    }
  },

  onStockCodeInput(event) {
    const code = event.detail;
    this.setData({ 
      stockCode: code,
      analysis: null
    });
    
    if (code.length >= 2) {
      this.searchStocks(code);
    } else {
      this.setData({ suggestions: [] });
    }
  },

  searchStocks(keyword) {
    wx.request({
      url: `${getApp().globalData.baseUrl}/api/stocks/search`,
      data: { keyword },
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          this.setData({ suggestions: res.data });
        }
      },
      fail: (error) => {
        console.error('搜索股票失败:', error);
      }
    });
  },

  onSelectStock(event) {
    const stock = event.currentTarget.dataset.stock;
    this.setData({
      stockCode: stock.code,
      stockName: stock.name,
      suggestions: [],
      analysis: null
    });
  },

  parseAnalysis(analysisStr) {
    try {
      // 尝试解析 JSON 字符串
      let analysisObj;
      try {
        analysisObj = JSON.parse(analysisStr);
      } catch (e) {
        // 如果解析失败，可能是字符串中的引号格式问题，尝试替换引号
        const cleanStr = analysisStr
          .replace(/[\u201c\u201d]/g, '"')  // 替换中文引号
          .replace(/```json\n?|\n?```/g, '') // 移除可能的 markdown 标记
          .replace(/\\/g, '')                // 移除转义字符
          .trim();
        analysisObj = JSON.parse(cleanStr);
      }

      const result = [];
      
      // 递归处理对象
      const processValue = (value, depth = 0) => {
        if (typeof value === 'object' && value !== null) {
          return Object.entries(value)
            .map(([k, v]) => {
              const indent = '  '.repeat(depth);
              if (typeof v === 'object' && v !== null) {
                return `${indent}${k}:\n${processValue(v, depth + 1)}`;
              }
              return `${indent}${k}: ${v}`;
            })
            .join('\n');
        }
        return String(value);
      };

      // 处理顶层属性
      for (const key in analysisObj) {
        const value = analysisObj[key];
        
        // 判断是否是详细信息
        const isDetails = typeof value === 'object' || 
                         String(value).length > 50 ||
                         key.match(/分析|详情|依据|评估|建议/);
        
        // 格式化内容
        const content = typeof value === 'object' ? 
          processValue(value) : 
          String(value);

        // 格式化标题
        const title = key.replace(/[""]/g, '')  // 移除引号
                        .replace(/[{}\[\]]/g, '') // 移除括号
                        .trim();

        result.push({
          title,
          content,
          isDetails
        });
      }
      
      return result;
    } catch (e) {
      console.error('解析分析结果失败:', e);
      // 如果解析失败，直接显示原始内容
      return [{
        title: '分析结果',
        content: analysisStr
          .replace(/```json\n?|\n?```/g, '')
          .replace(/[\u201c\u201d]/g, '"')
          .trim(),
        isDetails: true
      }];
    }
  },

  onAnalyze() {
    if (!this.data.stockCode) {
      wx.showToast({
        title: '请输入股票代码',
        icon: 'none'
      });
      return;
    }

    this.setData({ loading: true });
    wx.showLoading({ title: '询问AI中...' });
    
    // 先获取最新交易日期
    wx.request({
      url: `${getApp().globalData.baseUrl}/api/stocks/${this.data.stockCode}/latest-trade-date`,
      method: 'GET',
      success: (dateRes) => {
        if (dateRes.statusCode === 200 && dateRes.data.date) {
          // 获取到日期后进行分析
          wx.request({
            url: `${getApp().globalData.baseUrl}/api/ai/analysis/${this.data.stockCode}`,
            method: 'GET',
            data: { date: dateRes.data.date },
            success: (analysisRes) => {
              if (analysisRes.statusCode === 200 && analysisRes.data) {
                const parsedAnalysis = this.parseAnalysis(analysisRes.data.analysis);
                this.setData({
                  analysis: analysisRes.data.analysis,
                  analysisDate: analysisRes.data.analysis_date,
                  parsedAnalysis
                });
              } else {
                wx.showToast({
                  title: analysisRes.data?.error || '分析失败',
                  icon: 'none'
                });
              }
            },
            fail: () => {
              wx.showToast({
                title: '分析请求失败',
                icon: 'none'
              });
            },
            complete: () => {
              wx.hideLoading();
              this.setData({ loading: false });
            }
          });
        } else {
          wx.showToast({
            title: dateRes.data?.error || '获取交易日期失败',
            icon: 'none'
          });
          wx.hideLoading();
          this.setData({ loading: false });
        }
      },
      fail: () => {
        wx.showToast({
          title: '获取日期失败',
          icon: 'none'
        });
        wx.hideLoading();
        this.setData({ loading: false });
      }
    });
  }
}); 