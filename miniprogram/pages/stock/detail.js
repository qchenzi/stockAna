import { getStockDetail } from '../../utils/request';

Page({
  data: {
    code: '',
    stock: null,
    loading: false
  },

  onLoad(options) {
    this.setData({ code: options.code });
    this.loadStockDetail();
  },

  async loadStockDetail() {
    this.setData({ loading: true });
    try {
      const stock = await getStockDetail(this.data.code);
      this.setData({ stock });
    } catch (error) {
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      });
    } finally {
      this.setData({ loading: false });
    }
  }
}); 