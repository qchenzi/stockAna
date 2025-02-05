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
    const currentDate = this.data.date ? new Date(this.data.date).getTime() : this.data.currentDate;
    
    this.setData({ 
      showDatePicker: true,
      currentDate: currentDate,
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
    wx.showLoading({ title: '加载中...' });

    wx.request({
      url: `${getApp().globalData.baseUrl}/api/technical/scores`,
      method: 'GET',
      data: selectedDate ? { date: selectedDate } : {},
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.scores) {
          const latestDate = res.data.date;
          
          this.setData({
            scores: res.data.scores,
            date: latestDate,
            currentDate: new Date(latestDate).getTime()
          });
        } else if (res.statusCode === 404) {
          this.showError('所选日期无数据');
          this.setData({ scores: [] });
        } else {
          this.showError('加载失败');
        }
      },
      fail: (err) => {
        console.error('加载评分失败:', err);
        this.showError('加载失败');
      },
      complete: () => {
        wx.hideLoading();
      }
    });
  },

  showError(message) {
    wx.showToast({
      title: message,
      icon: 'none',
      duration: 2000
    });
  },

  onStockClick(event) {
    const stock = event.currentTarget.dataset.stock;
    wx.navigateTo({
      url: `/pages/stock/detail/index?code=${stock.stock_code}`,
      fail: (err) => {
        console.error('跳转详情页面失败:', err);
        this.showError('页面跳转失败');
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