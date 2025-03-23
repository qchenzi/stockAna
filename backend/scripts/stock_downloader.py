import yfinance as yf
import pandas as pd
import os
from datetime import datetime
import time
import json
import shutil
import concurrent.futures
import logging
from tqdm import tqdm
import requests
import random
import pkg_resources

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 检查 yfinance 版本
yf_version = pkg_resources.get_distribution('yfinance').version
logger.info(f"当前 yfinance 版本: {yf_version}")

def get_headers():
    """获取请求头"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }

def download_stock_info(args):
    """下载单个股票信息"""
    stock_code, stock_name, market, date_dir = args
    try:
        # 使用自定义的 session
        session = requests.Session()
        session.headers.update(get_headers())
        
        # 根据市场代码选择后缀
        suffix = '.SZ' if market == 'SZ' else '.SS'
        full_code = f"{stock_code}{suffix}"
        
        # 创建股票对象时传入 session
        stock = yf.Ticker(full_code, session=session)
        
        # 添加延时，避免请求过于频繁
        time.sleep(random.uniform(0, 1))
        
        max_retries = 1
        for attempt in range(max_retries):
            try:
                # 尝试不同的方法获取数据
                try:
                    info = stock.info
                except (ValueError, AttributeError):
                    # 如果 .info 失败，尝试获取基本信息
                    info = {
                        'symbol': full_code,
                        'shortName': stock_name,
                        'longName': stock_name,
                        'sector': '其他'
                    }
                    # 尝试获取最新报价
                    hist = stock.history(period="1d")
                    if not hist.empty:
                        info['regularMarketPrice'] = hist['Close'].iloc[-1]
                
                if not info:
                    raise ValueError(f"Empty response for {full_code}")
                break
                
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = 0.5
                    logger.warning(f"获取 {stock_name}({stock_code}) 失败: {str(e)}, "
                                 f"第 {attempt + 1}/{max_retries} 次重试，等待 {delay} 秒")
                    time.sleep(delay)
                    
                    if attempt % 3 == 2:
                        session = requests.Session()
                        session.headers.update(get_headers())
                        stock = yf.Ticker(full_code, session=session)
                    continue
                else:
                    return False, f"获取 {stock_name}({stock_code}) 的信息失败: {str(e)}"
        
        # 处理获取到的数据
        if info:
            sector = info.get('sector', 'Other')
            if not sector or sector == 'None':
                sector = '其他'
            
            # 创建板块目录
            sector_dir = os.path.join(date_dir, sector)
            os.makedirs(sector_dir, exist_ok=True)
            
            # 添加额外信息
            info['stock_code'] = stock_code
            info['stock_name'] = stock_name
            info['market'] = market
            
            # 保存股票信息
            file_path = os.path.join(sector_dir, f"{stock_code}_{stock_name}_info.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            
            return True, f"成功下载 {stock_name}({stock_code}) 的信息"
        else:
            return False, f"未获取到 {stock_name}({stock_code}) 的信息"
            
    except Exception as e:
        return False, f"获取 {stock_name}({stock_code}) 的信息时出错: {str(e)}"

def download_sh_stocks_info(max_workers=5):
    """下载股票信息"""
    try:
        # 尝试多个可能的文件路径
        possible_paths = [
            'data/stocks.csv',
            'stocks.csv',
            'stock_list.csv'
        ]
        
        df = None
        for path in possible_paths:
            try:
                df = pd.read_csv(path)
                logger.info(f"成功读取股票列表: {path}")
                break
            except FileNotFoundError:
                continue
                
        if df is None:
            logger.error("未找到股票列表文件，请确保以下文件之一存在：")
            for path in possible_paths:
                logger.error(f"- {path}")
            return 0
            
        # 确保列名正确
        if '代码' in df.columns:
            df = df.rename(columns={
                '代码': 'stock_code',
                '名称': 'stock_name',
                '市场': 'market'
            })
            
        logger.info(f"读取到 {len(df)} 只股票")

        # 创建主数据目录
        base_dir = 'stock_fundamental/stock_info'
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # 创建日期目录
        today = datetime.now().strftime('%Y-%m-%d')
        date_dir = os.path.join(base_dir, today)
        if os.path.exists(date_dir):
            shutil.rmtree(date_dir)
        os.makedirs(date_dir)

        # 准备下载任务
        download_tasks = [
            (str(row['stock_code']).zfill(6), row['stock_name'], row['market'], date_dir)
            for _, row in df.iterrows()
        ]

        # 使用线程池并发下载
        success_count = 0
        failed_stocks = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(download_stock_info, task) for task in download_tasks]
            
            # 使用tqdm显示进度
            for future in tqdm(concurrent.futures.as_completed(futures), 
                             total=len(futures), 
                             desc="下载进度"):
                success, message = future.result()
                if success:
                    success_count += 1
                else:
                    failed_stocks.append(message)
                logger.info(message)
                
                # 添加小延时避免请求过于频繁
                # time.sleep(0.2)

        logger.info(f"\n下载完成! 成功: {success_count}/{len(download_tasks)}")
        if failed_stocks:
            logger.warning("以下股票下载失败:")
            for msg in failed_stocks:
                logger.warning(msg)
        return success_count
        
    except Exception as e:
        logger.error(f"下载过程出错: {str(e)}")
        return 0

if __name__ == "__main__":
    logger.info("开始获取上证股票信息...")
    start_time = datetime.now()
    
    # 减少并发数，增加延时
    success_count = download_sh_stocks_info(max_workers=3)
    
    end_time = datetime.now()
    logger.info(f"总耗时: {end_time - start_time}") 