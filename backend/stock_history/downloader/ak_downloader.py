import os
import logging
import pandas as pd
import akshare as ak
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
import time
import random

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def format_date(date_str):
    """转换日期格式从 YYYY-MM-DD 到 YYYYMMDD"""
    if date_str:
        return date_str.replace('-', '')
    return None

class AKStockDownloader:
    def __init__(self, output_dir, max_workers=5, retry_times=10, retry_delay=5):
        """初始化下载器
        
        Args:
            output_dir (str): 输出目录
            max_workers (int): 最大并发数
            retry_times (int): 重试次数
            retry_delay (int): 重试延迟(秒)
        """
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.retry_times = retry_times
        self.retry_delay = retry_delay
        
    def download_stock_data(self, stock_code, start_date=None, end_date=None):
        """下载单只股票的历史数据"""
        for attempt in range(self.retry_times):
            try:
                # 添加随机延时，避免被封
                time.sleep(random.uniform(1, 3))
                
                # 获取股票名称
                try:
                    stock_info_df = ak.stock_info_a_code_name()
                    stock_name = stock_info_df[stock_info_df['code'] == stock_code]['name'].values[0]
                except Exception as e:
                    logger.warning(f"获取股票名称失败: {str(e)}")
                    stock_name = 'Unknown'
                
                # 构建股票代码（添加市场前缀）
                if stock_code.startswith('6'):
                    full_code = f"sh{stock_code}"
                else:
                    full_code = f"sz{stock_code}"
                    
                logger.info(f"下载 {stock_code} ({stock_name})...")
                
                # 转换日期格式
                formatted_start_date = format_date(start_date)
                formatted_end_date = format_date(end_date)
                
                # 下载数据
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=formatted_start_date,
                    end_date=formatted_end_date,
                    adjust="qfq"
                )
                
                if df.empty:
                    logger.error(f"{stock_code} ({stock_name}): 未获取到数据")
                    return False
                
                # 重命名列
                df = df.rename(columns={
                    '日期': 'Date',
                    '开盘': 'Open',
                    '收盘': 'Close',
                    '最高': 'High',
                    '最低': 'Low',
                    '成交量': 'Volume',
                    '成交额': 'Amount',
                    '振幅': 'Amplitude',
                    '涨跌幅': 'Change',
                    '涨跌额': 'ChangeAmount',
                    '换手率': 'Turnover'
                })
                
                # 设置日期为索引
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                
                # 添加额外列
                df['Dividends'] = 0.0
                df['Stock Splits'] = 0.0
                
                # 确保目录存在
                os.makedirs(self.output_dir, exist_ok=True)
                
                # 保存到CSV
                output_file = os.path.join(self.output_dir, f"{stock_code}_{stock_name}_history.csv")
                df.to_csv(output_file)
                
                logger.info(f"√ {stock_code} ({stock_name}): {len(df)}条记录")
                return True
                
            except Exception as e:
                if attempt < self.retry_times - 1:
                    logger.warning(f"× {stock_code}: 重试 {attempt + 1}/{self.retry_times}")
                else:
                    logger.error(f"× {stock_code}: 下载失败")
                time.sleep(self.retry_delay)
            
        return False
    
    def batch_download(self, stock_list_file, start_date=None, end_date=None):
        """批量下载多只股票的历史数据"""
        try:
            # 读取股票列表
            df = pd.read_csv(stock_list_file)
            stock_codes = df['代码'].astype(str).str.zfill(6).tolist()
            
            success_count = 0
            failed_stocks = []
            
            logger.info(f"开始下载 {len(stock_codes)} 只股票 ({start_date or '最早'} 至 {end_date or '最新'})")
            
            # 使用线程池并发下载
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 创建下载任务
                future_to_stock = {
                    executor.submit(self.download_stock_data, code, start_date, end_date): code 
                    for code in stock_codes
                }
                
                # 处理下载结果
                for future in tqdm(concurrent.futures.as_completed(future_to_stock), 
                                 total=len(stock_codes),
                                 desc="下载进度"):
                    stock_code = future_to_stock[future]
                    try:
                        if future.result():
                            success_count += 1
                        else:
                            failed_stocks.append(stock_code)
                    except Exception as e:
                        logger.error(f"处理 {stock_code} 时出错: {str(e)}")
                        failed_stocks.append(stock_code)
            
            # 输出统计信息
            logger.info(f"\n下载完成! 成功: {success_count}/{len(stock_codes)}")
            if failed_stocks:
                logger.warning("下载失败的股票:")
                for code in failed_stocks:
                    logger.warning(code)
                    
            return success_count
            
        except Exception as e:
            logger.error(f"批量下载过程出错: {str(e)}")
            return 0

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='使用AKShare下载股票历史数据')
    
    parser.add_argument('--output', '-o',
                       required=True,
                       help='输出目录路径')
    
    parser.add_argument('--stock-list', '-s',
                       required=True,
                       help='股票列表文件路径')
    
    parser.add_argument('--start-date',
                       help='开始日期(YYYY-MM-DD格式)')
    
    parser.add_argument('--end-date',
                       help='结束日期(YYYY-MM-DD格式)')
    
    parser.add_argument('--workers', '-w',
                       type=int,
                       default=3,
                       help='并发下载的线程数')
    
    args = parser.parse_args()
    
    # 创建下载器实例
    downloader = AKStockDownloader(
        output_dir=args.output,
        max_workers=args.workers
    )
    
    # 开始下载
    logger.info("开始下载历史交易数据...")
    start_time = datetime.now()
    
    success_count = downloader.batch_download(
        stock_list_file=args.stock_list,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    end_time = datetime.now()
    logger.info(f"总耗时: {end_time - start_time}")
    logger.info(f"成功下载: {success_count} 只股票的数据")

if __name__ == "__main__":
    main() 