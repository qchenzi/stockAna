// app.js
App({
  onLaunch() {
    // 屏蔽框架废弃API的警告
    console.warn = () => {};
    
    this.globalData = {
      userInfo: null,
      baseUrl: 'http://tech-chen.site'
    };
  }
});
