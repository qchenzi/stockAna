const app = getApp();

Page({
  data: {
    basic: {},
    quote: {},
    technical: {},
    fundamental: {},
    financial: {},
    investor: {},
    // 计算后的显示值
    priceChange: '-',
    priceChangePercent: '-',
    volumeDisplay: '-',
    amountDisplay: '-',
    roeDisplay: '-',
    revenueGrowthDisplay: '-',
    earningsGrowthDisplay: '-',
    dividendYieldDisplay: '-',
    debtToEquityDisplay: '-',
    cashFlowDisplay: '-',
    quoteDate: '-'
  },

  onLoad(options) {
    const { code } = options;
    this.loadStockDetails(code);
  },

  async loadStockDetails(code) {
    console.log('开始加载股票详情, 代码:', code);
    wx.showLoading({
      title: '加载中...'
    });

    try {
      const url = `${getApp().globalData.baseUrl}/api/stocks/${code}/details`;
      console.log('请求URL:', url);

      const res = await new Promise((resolve, reject) => {
        wx.request({
          url,
          method: 'GET',
          success: (res) => resolve(res),
          fail: (err) => reject(err)
        });
      });

      console.log('响应状态:', res.statusCode);
      console.log('响应数据:', res.data);

      if (res.statusCode === 200) {
        const { basic, quote, fundamental, financial } = res.data;
        console.log('解构数据:', { basic, quote, fundamental, financial });
        
        // 处理中文编码问题
        const decodedName = basic.name ? decodeURIComponent(basic.name.replace(/\\u/g, '%u')) : '-';
        
        // 计算显示值
        const priceChange = quote.close && quote.open ? 
          (quote.close - quote.open).toFixed(2) : '-';
        const priceChangePercent = quote.close && quote.open ? 
          ((quote.close - quote.open) / quote.open * 100).toFixed(2) : '-';
        const volumeDisplay = quote.volume ? 
          (quote.volume/10000).toFixed(2) + '万' : '-';
        const amountDisplay = quote.amount ? 
          (quote.amount/100000000).toFixed(2) + '亿' : '-';
        
        // 格式化日期
        const quoteDate = quote.date ? 
          quote.date.split('T')[0] : '-';
        
        this.setData({
          basic: {
            ...basic,
            name: decodedName
          },
          quote,
          technical: res.data.technical,
          fundamental,
          financial,
          investor: res.data.investor,
          priceChange,
          priceChangePercent,
          volumeDisplay,
          amountDisplay,
          roeDisplay: fundamental.roe ? fundamental.roe + '%' : '-',
          revenueGrowthDisplay: fundamental.revenueGrowth ? fundamental.revenueGrowth + '%' : '-',
          earningsGrowthDisplay: fundamental.earningsGrowth ? fundamental.earningsGrowth + '%' : '-',
          dividendYieldDisplay: fundamental.dividendYield ? fundamental.dividendYield + '%' : '-',
          debtToEquityDisplay: financial.debtToEquity ? financial.debtToEquity + '%' : '-',
          cashFlowDisplay: financial.operatingCashFlow ? 
            (financial.operatingCashFlow/100000000).toFixed(2) : '-',
          quoteDate
        });
      } else {
        wx.showToast({
          title: '获取数据失败',
          icon: 'none'
        });
      }
    } catch (error) {
      console.error('请求失败:', error);
      wx.showToast({
        title: '网络请求失败',
        icon: 'none'
      });
    } finally {
      wx.hideLoading();
    }
  },

  onViewKLineClick() {
    const { code } = this.data.basic;
    if (code) {
      wx.navigateTo({
        url: `/pages/technical/index?code=${code}&date=${this.data.quoteDate}`,
        fail: (err) => {
          console.error('跳转技术分析页面失败:', err);
          wx.showToast({
            title: '页面跳转失败',
            icon: 'none'
          });
        }
      });
    }
  },

  onViewAIAnalysisClick() {
    const { code } = this.data.basic;
    if (code) {
      wx.navigateTo({
        url: `/pages/ai-analysis/index?code=${code}&date=${this.data.quoteDate}`,
        fail: (err) => {
          console.error('跳转AI分析页面失败:', err);
          wx.showToast({
            title: '页面跳转失败',
            icon: 'none'
          });
        }
      });
    }
  }
}); 