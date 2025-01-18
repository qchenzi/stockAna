import { getStrategyList } from '../../utils/request';

Page({
  data: {
    strategies: []
  },

  onLoad() {
    this.loadStrategies();
  },

  async loadStrategies() {
    try {
      console.log('开始加载策略列表');
      const result = await getStrategyList();
      console.log('获取到的数据:', result);
      
      // 将对象转换为数组
      const strategiesArray = Object.entries(result.strategies).map(([key, value]) => ({
        ...value,
        key
      }));
      
      console.log('转换后的数组:', strategiesArray);
      this.setData({ strategies: strategiesArray });
    } catch (error) {
      console.error('加载策略失败:', error);
      wx.showToast({
        title: error.message || '加载失败',
        icon: 'none',
        duration: 2000
      });
    }
  },

  onStrategyTap(e) {
    const { key } = e.currentTarget.dataset;
    wx.navigateTo({
      url: `/pages/strategy/result?strategy=${key}`
    });
  }
}); 