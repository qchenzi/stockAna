// 获取 app 实例
const app = getApp();

// 使用全局配置的 baseUrl
const BASE_URL = app.globalData.baseUrl;

// 添加默认配置
const DEFAULT_OPTIONS = {
  method: 'GET',
  header: {
    'content-type': 'application/json'
  }
};

const request = (url, options = {}) => {
  console.log('开始请求:', `${BASE_URL}${url}`);
  
  wx.showLoading({ title: '加载中...' });
  
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${BASE_URL}${url}`,
      ...DEFAULT_OPTIONS,
      ...options,
      success: (res) => {
        console.log('请求成功:', res);
        if (res.statusCode === 200) {
          resolve(res.data);
        } else {
          console.error('请求失败:', res.statusCode, res.data);
          reject(new Error(`请求失败: ${res.statusCode}`));
        }
      },
      fail: (err) => {
        console.error('请求异常:', err);
        // 更详细的错误信息
        const errMsg = err.errMsg || '未知错误';
        if (errMsg.includes('timeout')) {
          reject(new Error('请求超时'));
        } else if (errMsg.includes('ssl')) {
          reject(new Error('SSL证书错误'));
        } else {
          reject(new Error(`网络请求失败: ${errMsg}`));
        }
      },
      complete: () => {
        wx.hideLoading();
      }
    });
  });
};

export const getStrategyList = () => {
  return request('/api/strategies');
};

export const getStrategyResult = (strategy, params = {}) => {
  return request(`/api/stocks/${strategy}`, {
    method: 'GET',
    data: params
  }).then(response => {
    // 如果返回的是字符串，需要处理 NaN 并解析
    if (typeof response === 'string') {
      try {
        // 将 NaN 替换为 null
        const cleanedResponse = response.replace(/: NaN/g, ': null');
        return JSON.parse(cleanedResponse);
      } catch (e) {
        console.error('解析返回数据失败:', e);
        throw e;
      }
    }
    return response;
  });
};

export const getStockDetail = (code) => {
  return request(`/api/stocks/${code}`);
};