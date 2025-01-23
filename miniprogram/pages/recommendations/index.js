Page({
  data: {
    date: '',
    recommendations: []
  },

  onLoad() {
    this.loadRecommendations();
  },

  loadRecommendations() {
    wx.showLoading({
      title: '加载中...',
    });

    wx.request({
      url: `${getApp().globalData.baseUrl}/api/technical/recommendations`,
      method: 'GET',
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          this.setData({
            recommendations: res.data.recommendations,
            date: res.data.date
          });
        }
      },
      fail: (err) => {
        wx.showToast({
          title: '加载失败',
          icon: 'error'
        });
      },
      complete: () => {
        wx.hideLoading();
      }
    });
  },

  onStockClick(event) {
    const stock = event.currentTarget.dataset.stock;
    wx.navigateTo({
      url: `/pages/stock/detail/index?code=${stock.stock_code}`,
      fail: (err) => {
        console.error('跳转详情页面失败:', err);
        wx.showToast({
          title: '页面跳转失败',
          icon: 'none'
        });
      }
    });
  }
}); 