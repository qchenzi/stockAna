import { getStrategyResult } from '../../utils/request';

Page({
  data: {
    strategy: '',
    summary: '',
    scoring_rules: [],
    stocks: [],
    loading: false,
    params: {
      top: 20,
      period: 14
    },
    showRules: false,
    indicatorDesc: []
  },

  onLoad(options) {
    console.log('策略页面参数:', options);
    this.setData({ 
      strategy: options.strategy
    });
    this.loadStrategyResult();
  },

  async loadStrategyResult() {
    try {
      this.setData({ loading: true });
      
      const { period, top } = this.data.params;
      const response = await getStrategyResult(this.data.strategy, { period, top });
      
      this.setData({
        strategy_desc: response.strategy_desc || '',
        scoring_rules: response.scoring_rules || [],
        stocks: response.stocks || [],
        loading: false
      });
      
    } catch (error) {
      console.error('加载策略结果失败:', error);
      this.setData({ loading: false });
    }
  },

  onStockTap(e) {
    console.log('点击股票:', e.currentTarget.dataset);
    const { stock } = e.currentTarget.dataset;
    if (stock && stock.code) {
      console.log('准备跳转到股票:', stock.code);
      wx.navigateTo({
        url: `/pages/stock/detail/index?code=${stock.code}`,
        success: () => console.log('跳转成功'),
        fail: (err) => console.error('跳转失败:', err)
      });
    } else {
      wx.showToast({
        title: '股票代码无效',
        icon: 'none'
      });
    }
  },

  onPeriodChange(e) {
    const period = parseInt(e.detail, 10);
    if (period > 0 && period <= 60) {  // 限制周期范围
      this.setData({
        'params.period': period
      });
      this.loadStrategyResult();  // 重新加载数据
    } else {
      wx.showToast({
        title: '周期应在1-60天之间',
        icon: 'none'
      });
    }
  },

  showPeriodTip() {
    wx.showModal({
      title: '计算周期说明',
      content: '计算周期影响RTPV策略的评分计算，建议值：\n' +
               '- 短期：7-14天\n' +
               '- 中期：15-30天\n' +
               '- 长期：31-60天',
      showCancel: false
    });
  },

  formatValue(value, type) {
    if (value === undefined || value === null) return '-';
    switch (type) {
      case 'percent':
        return (value * 100).toFixed(1) + '%';
      case 'decimal':
        return value.toFixed(2);
      case 'ratio':
        return value.toFixed(1);
      default:
        return value;
    }
  },

  getMetrics(item, strategy) {
    if (!item) return [];
    
    const baseInfo = [
      { label: '总分', value: item.score?.toFixed(1) || '-', isScore: true }
    ];
    
    if (!item.metrics) return baseInfo;
    
    const m = item.metrics;
    let extraMetrics = [];
    
    switch (strategy) {
      case 'rtpv':
        extraMetrics = [
          { label: '涨幅', value: this.formatValue(m['价格变动'], 'percent') },
          { label: '量比', value: this.formatValue(m['成交量比'], 'ratio') }
        ];
        break;
        
      case 'growth':
        extraMetrics = [
          { label: '营收增速', value: this.formatValue(m.revenue_growth, 'percent') },
          { label: '利润增速', value: this.formatValue(m.earnings_growth, 'percent') }
        ];
        break;
        
      // 添加其他策略的指标
      case 'value':
        extraMetrics = [
          { label: 'PE', value: this.formatValue(m.pe_ratio, 'decimal') },
          { label: 'ROE', value: this.formatValue(m.roe, 'percent') }
        ];
        break;
        
      case 'income':
        extraMetrics = [
          { label: '股息率', value: this.formatValue(m.dividend_yield, 'percent') },
          { label: 'β', value: this.formatValue(m.beta, 'decimal') }
        ];
        break;
        
      case 'trend':
        extraMetrics = [
          { label: 'RSI', value: this.formatValue(m.rsi, 'decimal') },
          { label: '量比', value: m.volume && m.avg_volume_10d ? 
            this.formatValue(m.volume / m.avg_volume_10d, 'ratio') : '-' }
        ];
        break;
        
      case 'reverse':
        const rebound = m.current_price && m.low_52week ? 
          ((m.current_price - m.low_52week) / m.low_52week) : null;
        extraMetrics = [
          { label: '反弹', value: this.formatValue(rebound, 'percent') },
          { label: 'ROE', value: this.formatValue(m.roe, 'percent') }
        ];
        break;
    }
    
    return [...baseInfo, ...extraMetrics];
  },

  formatLabel(item, strategy) {
    if (!item) return '';
    
    // 先只显示总分
    let label = `总分: ${item.score?.toFixed(1)}`;
    
    // 如果没有 metrics 就只返回总分
    if (!item.metrics) return label;
    
    // 根据策略添加指标
    const m = item.metrics;
    if (strategy === 'rtpv') {
      label += ` | 涨幅: ${m['价格变动']}% | 量比: ${m['成交量比']}`;
    }
    
    return label;
  },

  toggleRules() {
    this.setData({
      showRules: !this.data.showRules
    });
  },

  getIndicatorIcon(indicator) {
    const iconMap = {
      'ROE': 'profit',
      'PE': 'valuation',
      '毛利率': 'margin',
      '市净率': 'pb',
      '营收增速': 'growth',
      '净利润增速': 'earnings',
      '技术趋势': 'trend',
      '流动比率': 'liquidity',
      '股息率': 'dividend',
      '分红持续性': 'history',
      '经营现金流': 'cashflow',
      'β': 'beta',
      '均线系统': 'ma',
      'MACD': 'macd',
      'RSI': 'rsi',
      '量比': 'volume',
      '超跌程度': 'oversold',
      '技术反转': 'reversal',
      '资金流向': 'capital',
      '基本面': 'fundamental'
    };
    return iconMap[indicator] || 'default';
  }
}); 