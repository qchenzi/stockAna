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
      const analysisObj = JSON.parse(analysisStr);
      const result = [];

      // 遍历对象的每个顶级属性
      for (const key in analysisObj) {
        const value = analysisObj[key];
        
        if (typeof value === 'object') {
          // 如果值是对象，递归处理
          const details = Object.entries(value)
            .map(([subKey, subValue]) => {
              if (typeof subValue === 'object') {
                return `${subKey}:\n${Object.entries(subValue)
                  .map(([k, v]) => `  ${k}: ${v}`).join('\n')}`;
              }
              return `${subKey}: ${subValue}`;
            })
            .join('\n\n');
          
          result.push({
            title: key,
            content: details,
            isDetails: true
          });
        } else {
          // 如果值是简单类型
          result.push({
            title: key,
            content: value,
            isDetails: false
          });
        }
      }
      
      return result;
    } catch (e) {
      console.error('解析分析结果失败:', e);
      return [{
        title: '分析结果',
        content: analysisStr,
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
    wx.showLoading({ title: 'AI分析中...' });
    
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