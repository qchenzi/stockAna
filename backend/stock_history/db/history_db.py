import logging
from datetime import datetime
import pandas as pd
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import glob
from tqdm import tqdm
import concurrent.futures

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from config.database import DB_CONFIG

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_engine():
    """创建数据库连接引擎"""
    connection_str = (
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
        f"{DB_CONFIG['host']}/{DB_CONFIG['database']}?charset=utf8mb4"
    )
    try:
        engine = create_engine(connection_str)
        # 测试连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("数据库连接成功")
        return engine
    except SQLAlchemyError as e:
        logger.error(f"数据库连接失败: {str(e)}")
        raise

def ensure_stock_exists(engine, stock_code, stock_name):
    """确保股票基本信息存在"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT 1 FROM stocks WHERE stock_code = :code"
            ), {'code': stock_code}).scalar()
            
            if not result:
                conn.execute(text("""
                    INSERT INTO stocks (stock_code, stock_name)
                    VALUES (:code, :name)
                """), {
                    'code': stock_code,
                    'name': stock_name
                })
                conn.commit()
                logger.info(f"已创建股票基本信息: {stock_code}")
        return True
    except Exception as e:
        logger.error(f"确保股票存在时出错: {str(e)}")
        return False

def import_csv_to_db(engine, csv_file, mode='all', start_date=None, end_date=None):
    """导入CSV文件到数据库"""
    try:
        # 读取CSV
        df = pd.read_csv(csv_file)
        
        # 处理日期列
        df['Date'] = pd.to_datetime(df['Date'])
        
        # 从文件名获取股票代码和来源信息
        filename = os.path.basename(csv_file)
        stock_code = filename.split('_')[0]
        source = 'akshare' if 'Amount' in df.columns else 'yfinance'
        
        # 重命名列以匹配数据库
        column_mappings = {
            'Date': 'trade_date',
            'Open': 'open_price',
            'Close': 'close_price',
            'High': 'high_price',
            'Low': 'low_price',
            'Volume': 'volume',
            'Dividends': 'dividends',
            'Stock Splits': 'stock_splits'
        }
        
        # AKShare 特有的列
        if source == 'akshare':
            column_mappings.update({
                'Amount': 'amount',
                'Amplitude': 'amplitude',
                'Change': 'change_ratio',
                'ChangeAmount': 'change_amount',
                'Turnover': 'turnover_ratio'
            })
        
        df = df.rename(columns=column_mappings)
        
        # 添加固定字段
        df['stock_code'] = stock_code
        df['source'] = source
        df['adjust_type'] = 'qfq'
        
        # 对于 yfinance 数据，计算缺失的字段
        if source == 'yfinance':
            df['amount'] = df['volume'] * df['close_price']  # 估算成交额
            df['amplitude'] = ((df['high_price'] - df['low_price']) / df['close_price'].shift(1) * 100).round(2)
            df['change_ratio'] = ((df['close_price'] - df['close_price'].shift(1)) / df['close_price'].shift(1) * 100).round(2)
            df['change_amount'] = (df['close_price'] - df['close_price'].shift(1)).round(2)
            df['turnover_ratio'] = 0  # yfinance 无法获取换手率
        
        # 日期过滤
        if mode == 'date_range' and start_date and end_date:
            df = df[
                (df['trade_date'] >= start_date) & 
                (df['trade_date'] <= end_date)
            ]
        
        # 写入数据库
        with engine.begin() as conn:
            # 使用原生SQL进行REPLACE INTO操作
            for _, row in df.iterrows():
                conn.execute(text("""
                    REPLACE INTO stock_historical_quotes (
                        stock_code, trade_date, open_price, close_price, 
                        high_price, low_price, volume, amount,
                        amplitude, change_ratio, change_amount, turnover_ratio,
                        source, adjust_type, dividends, stock_splits
                    ) VALUES (
                        :stock_code, :trade_date, :open_price, :close_price,
                        :high_price, :low_price, :volume, :amount,
                        :amplitude, :change_ratio, :change_amount, :turnover_ratio,
                        :source, :adjust_type, :dividends, :stock_splits
                    )
                """), row.to_dict())
            
        return len(df)
        
    except Exception as e:
        logger.error(f"导入 {csv_file} 失败: {str(e)}")
        logger.error(f"错误详情: {str(e)}")  # 添加更详细的错误信息
        return 0

def batch_import_historical_data(data_dir, mode='all', start_date=None, end_date=None, max_workers=5):
    """批量导入历史数据
    
    Args:
        data_dir (str): 数据目录路径
        mode (str): 导入模式
            - 'all': 导入所有数据
            - 'date_range': 导入指定日期范围的数据
        start_date (str): 开始日期 (YYYY-MM-DD)
        end_date (str): 结束日期 (YYYY-MM-DD)
        max_workers (int): 并发工作线程数
    """
    try:
        engine = get_db_engine()
        success_count = 0
        failed_files = []
        
        # 获取所有CSV文件
        csv_files = []
        for root, _, files in os.walk(data_dir):
            for file in files:
                if file.endswith('_history.csv'):
                    csv_files.append(os.path.join(root, file))
                    
        logger.info(f"找到 {len(csv_files)} 个CSV文件")
        
        # 使用线程池并发导入
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(import_csv_to_db, engine, csv_file, mode=mode, start_date=start_date, end_date=end_date): csv_file 
                for csv_file in csv_files
            }
            
            # 处理结果
            for future in tqdm(concurrent.futures.as_completed(future_to_file), 
                             total=len(csv_files), 
                             desc="导入进度"):
                csv_file = future_to_file[future]
                try:
                    if future.result():
                        success_count += 1
                    else:
                        failed_files.append(csv_file)
                except Exception as e:
                    logger.error(f"处理文件 {csv_file} 时出错: {str(e)}")
                    failed_files.append(csv_file)
                
        logger.info(f"\n导入完成! 成功: {success_count}/{len(csv_files)}")
        if failed_files:
            logger.warning("以下文件导入失败:")
            for file in failed_files:
                logger.warning(file)
                
        return success_count
        
    except Exception as e:
        logger.error(f"批量导入过程出错: {str(e)}")
        return 0

def delete_historical_data(engine, stock_code=None, start_date=None, end_date=None):
    """删除指定范围的历史数据
    
    Args:
        engine: 数据库连接引擎
        stock_code (str, optional): 股票代码。如果不指定，则删除所有股票的数据
        start_date (str, optional): 开始日期 (YYYY-MM-DD)
        end_date (str, optional): 结束日期 (YYYY-MM-DD)
    
    Returns:
        int: 删除的记录数
    """
    try:
        conditions = []
        params = {}
        
        # 构建 WHERE 子句
        if stock_code:
            conditions.append("stock_code = :stock_code")
            params['stock_code'] = stock_code
            
        if start_date:
            conditions.append("trade_date >= :start_date")
            params['start_date'] = start_date
            
        if end_date:
            conditions.append("trade_date <= :end_date")
            params['end_date'] = end_date
            
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 构建删除语句
        delete_sql = f"""
            DELETE FROM stock_historical_quotes 
            WHERE {where_clause}
        """
        
        # 执行删除
        with engine.connect() as conn:
            result = conn.execute(text(delete_sql), params)
            conn.commit()
            deleted_count = result.rowcount
            
            logger.info(f"已删除 {deleted_count} 条记录")
            logger.info(f"删除条件: {where_clause}")
            logger.info(f"参数: {params}")
            
            return deleted_count
            
    except Exception as e:
        logger.error(f"删除数据时出错: {str(e)}")
        return 0

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='股票历史交易数据管理工具')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 导入数据的命令
    import_parser = subparsers.add_parser('import', help='导入历史数据')
    import_parser.add_argument('--data-dir', '-d',
                             required=True,
                             help='数据目录路径')
    import_parser.add_argument('--mode', '-m',
                             choices=['all', 'date_range'],
                             default='all',
                             help='导入模式: all=所有数据, date_range=指定日期范围')
    import_parser.add_argument('--start-date',
                             help='开始日期(YYYY-MM-DD格式)')
    import_parser.add_argument('--end-date',
                             help='结束日期(YYYY-MM-DD格式)')
    import_parser.add_argument('--workers', '-w',
                             type=int, 
                             default=5,
                             help='并发工作线程数')
    
    # 删除数据的命令
    delete_parser = subparsers.add_parser('delete', help='删除历史数据')
    delete_parser.add_argument('--stock-code', '-s',
                             help='股票代码（可选）')
    delete_parser.add_argument('--start-date',
                             required=True,
                             help='开始日期(YYYY-MM-DD格式)')
    delete_parser.add_argument('--end-date',
                             required=True,
                             help='结束日期(YYYY-MM-DD格式)')
    
    args = parser.parse_args()
    
    if args.command == 'import':
        logger.info("开始导入历史交易数据...")
        start_time = datetime.now()
        
        success_count = batch_import_historical_data(
            data_dir=args.data_dir,
            mode=args.mode,
            start_date=args.start_date,
            end_date=args.end_date,
            max_workers=args.workers
        )
        
        end_time = datetime.now()
        logger.info(f"总耗时: {end_time - start_time}")
        logger.info(f"成功导入: {success_count} 只股票的数据")
        
    elif args.command == 'delete':
        logger.info("开始删除历史交易数据...")
        start_time = datetime.now()
        
        engine = get_db_engine()
        deleted_count = delete_historical_data(
            engine=engine,
            stock_code=args.stock_code,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        end_time = datetime.now()
        logger.info(f"总耗时: {end_time - start_time}")
        logger.info(f"成功删除: {deleted_count} 条记录") 