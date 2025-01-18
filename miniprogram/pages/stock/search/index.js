const app = getApp();

Page({
  data: {
    stockCode: '',
    suggestions: []
  },

  onStockCodeInput(event) {
    const code = event.detail;
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
          url: `${app.globalData.baseUrl}/api/stocks/search`,
          data: { keyword },
          success: resolve,
          fail: reject
        });
      });

      if (res.statusCode === 200 && res.data) {
        this.setData({ suggestions: res.data });
      }
    } catch (error) {
      console.error('搜索股票失败:', error);
    }
  },

  onSelectStock(event) {
    const { code } = event.currentTarget.dataset.stock;
    wx.navigateTo({
      url: `/pages/stock/detail/index?code=${code}`
    });
  }
}); 