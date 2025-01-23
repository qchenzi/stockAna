import { getStrategyList } from '../../utils/request';

Page({
  data: {},

  // 跳转到策略选股页面
  onStrategyTap() {
    console.log('点击策略选股');
    wx.navigateTo({
      url: '/pages/strategy/list'
    });
  },

  // 添加新的导航方法
  navigateToTechnical() {
    console.log('点击K线指标');
    wx.navigateTo({
      url: '/pages/technical/index',
      success: () => {
        console.log('跳转成功');
      },
      fail: (err) => {
        console.error('跳转失败:', err);
      }
    });
  },

  onStrategyClick() {
    wx.navigateTo({
      url: '/pages/strategy/list'
    });
  },

  onTechnicalClick() {
    wx.navigateTo({
      url: '/pages/technical/index'
    });
  },

  onStockInfoClick() {
    wx.navigateTo({
      url: '/pages/stock/search/index'
    });
  },

  onAIAnalysisClick() {
    wx.navigateTo({
      url: '/pages/ai-analysis/index'
    });
  },

  onWatchlistClick() {
    wx.navigateTo({
      url: '/pages/watchlist/index'
    });
  },

  onRecommendationsClick() {
    wx.navigateTo({
      url: '/pages/recommendations/index'
    });
  }
}); 