// app.js
App({
  onLaunch() {
    // 屏蔽框架废弃API的警告
    console.warn = () => {};
    
    this.globalData = {
      userInfo: null,
      baseUrl: 'http://backend_server_ip:5000' // backend服务地址
    };
  }
});
