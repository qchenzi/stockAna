Page({
  data: {
    date: '',
    scores: [],
    showDatePicker: false,
    currentDate: new Date().getTime(),
    minDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).getTime(),
    maxDate: new Date().getTime()
  },

  onLoad() {
    this.loadScores();
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
    const formattedDate = new Date(date.getTime() - (date.getTimezoneOffset() * 60000))
      .toISOString()
      .split('T')[0];
    
    this.setData({
      date: formattedDate,
      showDatePicker: false,
      currentDate: date.getTime()
    });

    this.loadScores(formattedDate);
  },

  loadScores(selectedDate = '') {
    wx.showLoading({
      title: '加载中...',
    });

    wx.request({
      url: `${getApp().globalData.baseUrl}/api/technical/scores`,
      method: 'GET',
      data: selectedDate ? { date: selectedDate } : {},
      success: (res) => {
        console.log('API Response:', res.data);
        if (res.data && res.data.scores) {
          console.log('First score:', res.data.scores[0]);
          if (!selectedDate) {
            this.setData({
              currentDate: new Date(res.data.date).getTime()
            });
          }
          
          this.setData({
            scores: res.data.scores,
            date: res.data.date
          });
        } else {
          wx.showToast({
            title: '加载失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        console.error('加载评分失败:', err);
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
  },

  getTrendClass(status) {
    switch(status) {
      case '强势上涨': return 'strong';
      case '短期向好': return 'good';
      case '盘整': return 'normal';
      default: return 'weak';
    }
  },

  getVolumeClass(status) {
    switch(status) {
      case '放量': return 'strong';
      case '缩量': return 'weak';
      default: return 'normal';
    }
  },

  getVolatilityClass(status) {
    return status === '剧烈波动' ? 'strong' : 'normal';
  },

  getBollingerClass(status) {
    switch(status) {
      case '超买': return 'strong';
      case '超卖': return 'weak';
      default: return 'normal';
    }
  }
}); 