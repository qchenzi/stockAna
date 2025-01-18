Page({
  // ... 其他代码

  onStockTap(event) {
    const { code } = event.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/stock/detail/index?code=${code}`
    });
  }
}); 