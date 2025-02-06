Page({
  data: {
    date: '',
    activeTab: 'buy_dip',
    stocks: [],
    showDatePicker: false,
    currentDate: new Date().getTime(),
    minDate: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).getTime(),
    maxDate: new Date().getTime(),
    tabs: [
      { name: '低吸', type: 'buy_dip' },
      { name: '追涨', type: 'follow_up' },
      { name: '潜力', type: 'potential' }
    ]
  },

  onLoad() {
    this.loadStocks();
  },

  onTabChange(event) {
    const type = event.detail.name;
    this.setData({ activeTab: type });
    this.loadStocks(this.data.date, type);
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

    this.loadStocks(formattedDate, this.data.activeTab);
  },

  loadStocks(selectedDate = '', type = 'buy_dip') {
    wx.showLoading({ title: '加载中...' });

    wx.request({
      url: `${getApp().globalData.baseUrl}/api/chip/analysis`,
      method: 'GET',
      data: {
        date: selectedDate,
        type: type
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          if (!selectedDate) {
            this.setData({
              currentDate: new Date(res.data.date).getTime()
            });
          }
          
          this.setData({
            stocks: res.data.stocks,
            date: res.data.date
          });
        } else if (res.statusCode === 404) {
          this.showError('所选日期无数据');
          this.setData({ stocks: [] });
        } else {
          this.showError('加载失败');
        }
      },
      fail: (err) => {
        console.error('加载筹码分析失败:', err);
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
  }
}); 