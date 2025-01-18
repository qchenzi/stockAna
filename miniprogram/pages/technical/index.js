const app = getApp();

Page({
  data: {
    stockCode: '',
    date: '',
    showCalendar: false,
    hasData: false,
    maData: {},
    crossData: {},
    threeBullish: {},
    engulfing: {},
    support: '',
    resistance: '',
    minDate: new Date(new Date().setMonth(new Date().getMonth() - 6)).getTime(),
    maxDate: new Date().getTime(),
    suggestions: []
  },

  onStockCodeChange(event) {
    this.setData({
      stockCode: event.detail
    });
  },

  showDatePicker() {
    this.setData({
      showCalendar: true
    });
  },

  onCloseCalendar() {
    this.setData({
      showCalendar: false
    });
  },

  onSelectDate(event) {
    const date = new Date(event.detail);
    const formattedDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    this.setData({
      date: formattedDate,
      showCalendar: false
    });
  },

  async queryTechnical() {
    const { stockCode, date } = this.data;
    if (!stockCode || !date) {
      this.showErrorMessage('请输入股票代码和日期');
      return;
    }

    // 检查是否为周末
    const selectedDate = new Date(date);
    const dayOfWeek = selectedDate.getDay();
    if (dayOfWeek === 0 || dayOfWeek === 6) {
      this.showErrorMessage('所选日期为周末非交易日');
      return;
    }

    wx.showLoading({
      title: '加载中...'
    });

    // 直接使用 wx.request，不使用 Promise
    wx.request({
      url: `${app.globalData.baseUrl}/api/technical/ma/${stockCode}`,
      data: { date },
      success: async (res) => {
        if (res.statusCode === 404) {
          wx.hideLoading();
          this.showErrorMessage('所选日期为非交易日或节假日');
          return;
        }

        if (res.statusCode !== 200) {
          wx.hideLoading();
          this.showErrorMessage('获取数据失败');
          return;
        }

        try {
          const maData = { data: res.data };
          const [crossData, bullishData, engulfingData, supportData] = await Promise.all([
            this.requestData('cross'),
            this.requestData('three-bullish'),
            this.requestData('engulfing'),
            this.requestData('support-resistance')
          ]);

          // 检查返回的数据
          if (!maData.data || !crossData.data || !bullishData.data || !engulfingData.data || !supportData.data) {
            throw new Error('数据不完整');
          }

          this.setData({
            hasData: true,
            maData: {
              ma5: maData.data.ma_5?.toFixed(2) || '-',
              ma10: maData.data.ma_10?.toFixed(2) || '-',
              ma20: maData.data.ma_20?.toFixed(2) || '-',
              ma60: maData.data.ma_60?.toFixed(2) || '-',
              ma200: maData.data.ma_200?.toFixed(2) || '-'
            },
            crossData: {
              signal: crossData.data.cross_type || '-',
              strength: `可信度: ${crossData.data.reliability_score}分 (强度: ${crossData.data.cross_strength.toFixed(2)}%, 量比: ${crossData.data.volume_ratio.toFixed(2)})`
            },
            threeBullish: {
              formed: bullishData.data.pattern_type === '三连阳',
              increase: bullishData.data.pattern_strength === '非三连阳' ? 
                '否' : 
                `${bullishData.data.pattern_strength} (可信度:${bullishData.data.reliability_score}分, 累计涨幅:${bullishData.data.total_gain}%)`
            },
            engulfing: {
              type: engulfingData.data.engulfing_type === 'Bullish' ? '看涨吞没' : 
                     engulfingData.data.engulfing_type === 'Bearish' ? '看跌吞没' : 
                     '无形态',
              reliability: engulfingData.data.reliability ? 
                `可信度: ${engulfingData.data.reliability_level}(${engulfingData.data.reliability}分)` : 
                '-'
            },
            support: `${supportData.data.support_levels['20d'].toFixed(2)} (${supportData.data.support_reliability}, ${supportData.data.support_strength})`,
            resistance: `${supportData.data.resistance_levels['20d'].toFixed(2)} (${supportData.data.resistance_reliability}, ${supportData.data.resistance_strength})`,
            pricePosition: `${supportData.data.price_position}，${supportData.data.price_range_position}，${supportData.data.volume_character}`
          });
        } catch (error) {
          console.error('获取数据失败:', error);
          this.showErrorMessage('获取数据失败');
        }
        wx.hideLoading();
      },
      fail: () => {
        wx.hideLoading();
        this.showErrorMessage('网络请求失败');
      }
    });
  },

  // 统一的错误消息显示方法
  showErrorMessage(message) {
    this.setData({ hasData: false });
    wx.showToast({
      title: message,
      icon: 'none',
      duration: 2500  // 增加显示时间
    });
  },

  requestData(endpoint) {
    const { stockCode, date } = this.data;
    const app = getApp();
    const baseUrl = `${app.globalData.baseUrl}/api/technical`;
    
    return new Promise((resolve, reject) => {
      wx.request({
        url: `${baseUrl}/${endpoint}/${stockCode}`,
        data: { date },
        success: (res) => {
          console.log(`${endpoint} 接口返回:`, res);
          if (res.statusCode === 200) {
            const data = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
            resolve({ data });
          } else if (res.statusCode === 404) {
            reject(new Error('当前日期无交易数据'));
          } else {
            reject(new Error(`请求失败: ${res.statusCode}`));
          }
        },
        fail: (err) => {
          console.error(`${endpoint} 接口错误:`, err);
          reject(err);
        }
      });
    });
  },

  onLoad(options) {
    // 处理从其他页面传入的参数
    if (options.code) {
      this.setData({ stockCode: options.code });
    }
    if (options.date) {
      this.setData({ date: options.date });
      // 自动查询数据
      this.queryTechnical();
    }
  },

  // 输入时触发
  onStockCodeInput(event) {
    const code = event.detail;
    if (code.length >= 2) {
      this.searchStocks(code);
    } else {
      this.setData({ suggestions: [] });
    }
  },

  // 搜索股票
  async searchStocks(keyword) {
    try {
      const res = await new Promise((resolve, reject) => {
        wx.request({
          url: `${getApp().globalData.baseUrl}/api/stocks/search`,
          data: { keyword },
          success: resolve,
          fail: reject
        });
      });

      if (res.statusCode === 200 && res.data) {
        this.setData({
          suggestions: res.data  // 显示所有数据
        });
      }
    } catch (error) {
      console.error('搜索股票失败:', error);
    }
  },

  // 选择股票
  onSelectStock(event) {
    const { code, name } = event.currentTarget.dataset.stock;
    this.setData({
      stockCode: code,
      suggestions: []  // 清空建议列表
    });
  }
}); 