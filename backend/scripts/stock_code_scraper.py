import requests
import pandas as pd
import json

def get_stock_list():
    # 东方财富 A 股列表 API
    url = "http://80.push2.eastmoney.com/api/qt/clist/get"
    
    # 分别获取上证和深证的股票
    market_params = [
        {
            'fs': 'm:1+t:2,m:1+t:23',  # 上海A股
            'name': 'sh'
        },
        {
            'fs': 'm:0+t:6,m:0+t:80',  # 深圳A股
            'name': 'sz'
        }
    ]
    
    all_stocks = []
    
    for market in market_params:
        params = {
            'pn': '1',  # 页码
            'pz': '10000',  # 每页数量
            'po': '1',
            'np': '1',
            'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
            'fltt': '2',
            'invt': '2',
            'fid': 'f3',
            'fs': market['fs'],
            'fields': 'f12,f14',  # f12是代码，f14是名称
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive'
        }
        
        try:
            print(f"\nFetching {market['name'].upper()} stocks...")
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and 'diff' in data['data']:
                stock_list = data['data']['diff']
                
                # 转换为 DataFrame
                df = pd.DataFrame(stock_list)
                df.columns = ['代码', '名称']
                
                # 处理股票代码，补零到6位
                df['代码'] = df['代码'].astype(str).str.zfill(6)
                
                # 添加市场标识
                df['市场'] = market['name'].upper()
                
                # 保存到单独的文件
                filename = f"{market['name']}_stock_list.csv"
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                print(f"保存{market['name'].upper()}股票列表到 {filename}")
                print(f"获取到 {len(df)} 只{market['name'].upper()}股票")
                
                all_stocks.append(df)
            else:
                print(f"No data found for {market['name'].upper()} stocks")
                
        except Exception as e:
            print(f"Error fetching {market['name'].upper()} stocks: {str(e)}")
    
    if all_stocks:
        # 合并所有股票数据
        final_df = pd.concat(all_stocks, ignore_index=True)
        
        # 保存完整数据
        final_df.to_csv('all_stock_list.csv', index=False, encoding='utf-8-sig')
        print("\nData saved successfully!")
        print(f"\n总共获取到 {len(final_df)} 只A股股票")
        print("\n按市场统计:")
        print(final_df['市场'].value_counts())
        
        # 显示每个市场的前几只股票
        print("\n上证市场前3只股票:")
        print(final_df[final_df['市场'] == 'SH'].head(3))
        print("\n深证市场前3只股票:")
        print(final_df[final_df['市场'] == 'SZ'].head(3))
        
        return final_df
    else:
        print("No data retrieved")
        return None

if __name__ == "__main__":
    get_stock_list()
