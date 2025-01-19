Page({
  data: {
    keyword: '',
    suggestions: [],
    watchlist: [],
  },

  onLoad() {
    this.loadWatchlist();
  },

  onShow() {
    // 每次显示页面时更新股票价格
    this.updateStockPrices();
  },

  loadWatchlist() {
    const watchlist = wx.getStorageSync('watchlist') || [];
    this.setData({ watchlist });
  },

  saveWatchlist() {
    wx.setStorageSync('watchlist', this.data.watchlist);
  },

  onSearchChange(event) {
    const keyword = event.detail;
    this.setData({ keyword });
    
    if (keyword.length >= 2) {
      this.searchStocks(keyword);
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
          // 过滤掉已添加的股票
          const watchlistCodes = this.data.watchlist.map(item => item.code);
          const suggestions = res.data.filter(item => !watchlistCodes.includes(item.code));
          this.setData({ suggestions });
        }
      }
    });
  },

  onAddStock(event) {
    const stock = event.currentTarget.dataset.stock;
    const watchlist = [...this.data.watchlist];
    
    // 检查是否已经添加过
    if (watchlist.some(item => item.code === stock.code)) {
      wx.showToast({
        title: '已在自选股中',
        icon: 'none'
      });
      return;
    }
    
    watchlist.push(stock);
    
    this.setData({
      watchlist,
      suggestions: [],
      keyword: ''
    });
    
    this.saveWatchlist();
    this.updateStockPrices();

    wx.showToast({
      title: '添加成功',
      icon: 'success'
    });
  },

  onDeleteStock(event) {
    const index = event.currentTarget.dataset.index;
    const watchlist = this.data.watchlist.filter((_, i) => i !== index);
    
    this.setData({ watchlist });
    this.saveWatchlist();
  },

  onStockClick(event) {
    const stock = event.currentTarget.dataset.stock;
    wx.navigateTo({
      url: `/pages/stock/detail/index?code=${stock.code}`
    });
  },

  updateStockPrices() {
    const { watchlist } = this.data;
    if (!watchlist.length) return;

    const codes = watchlist.map(item => item.code);
    
    wx.request({
      url: `${getApp().globalData.baseUrl}/api/stocks/quotes`,
      method: 'POST',
      data: { codes },
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const updatedWatchlist = watchlist.map(stock => {
            const quote = res.data[stock.code];
            if (quote) {
              const change = ((quote.price - quote.pre_close) / quote.pre_close * 100).toFixed(2);
              return {
                ...stock,
                price: quote.price.toFixed(2),
                change: change > 0 ? `+${change}%` : `${change}%`,
                changeClass: change > 0 ? 'up' : 'down'
              };
            }
            return stock;
          });
          
          this.setData({ watchlist: updatedWatchlist });
        }
      }
    });
  }
}); 