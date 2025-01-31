Page({
  data: {
    date: '',
    recommendations: [],
    showDatePicker: false,
    currentDate: new Date().getTime(),
    minDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).getTime(),
    maxDate: new Date().getTime()
  },

  onLoad() {
    // 默认加载最新的推荐
    this.loadRecommendations();
  },

  onShowDatePicker() {
    this.setData({ 
      showDatePicker: true,
      maxDate: new Date().getTime(),
      minDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).getTime()
    });
  },

  onCloseDatePicker() {
    this.setData({ showDatePicker: false });
  },

  onDateConfirm(event) {
    const date = new Date(event.detail);
    // 使用 UTC 时间来避免时区问题
    const formattedDate = new Date(date.getTime() - (date.getTimezoneOffset() * 60000))
      .toISOString()
      .split('T')[0];
    
    this.setData({
      date: formattedDate,
      showDatePicker: false,
      currentDate: date.getTime()
    });

    // 加载选中日期的推荐
    this.loadRecommendations(formattedDate);
  },

  loadRecommendations(selectedDate = '') {
    wx.showLoading({
      title: '加载中...',
    });

    console.log('请求日期:', selectedDate); // 添加日志

    wx.request({
      url: `${getApp().globalData.baseUrl}/api/technical/recommendations`,
      method: 'GET',
      data: selectedDate ? { date: selectedDate } : {},
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          // 如果是首次加载（没有选择日期），更新当前日期
          if (!selectedDate) {
            this.setData({
              currentDate: new Date(res.data.date).getTime()
            });
          }
          
          this.setData({
            recommendations: res.data.recommendations,
            date: res.data.date
          });
        } else if (res.statusCode === 404) {
          wx.showToast({
            title: '所选日期无数据',
            icon: 'none',
            duration: 2000
          });
          this.setData({ recommendations: [] });
        }
      },
      fail: (err) => {
        console.error('加载推荐失败:', err);
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