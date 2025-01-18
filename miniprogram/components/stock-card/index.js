Component({
  properties: {
    stock: {
      type: Object,
      value: {}
    }
  },
  
  methods: {
    onTap() {
      const { code } = this.data.stock;
      wx.navigateTo({
        url: `/pages/stock/detail?code=${code}`
      });
    }
  }
}); 