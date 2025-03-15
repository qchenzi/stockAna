import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from config.database import DB_CONFIG
import os
import json
import argparse
import concurrent.futures
from queue import Queue
from threading import Lock
import glob

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加计数器类来安全计数
class Counter:
    def __init__(self):
        self.value = 0
        self.lock = Lock()
    
    def increment(self):
        with self.lock:
            self.value += 1
            return self.value

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

def log_update(engine, table_name, update_type, start_time, status, records_affected=0, error_message=None):
    """记录数据更新日志"""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO update_logs (table_name, update_type, start_time, end_time, status, records_affected, error_message)
                VALUES (:table, :type, :start, :end, :status, :records, :error)
            """), {
                'table': table_name,
                'type': update_type,
                'start': start_time,
                'end': datetime.now(),
                'status': status,
                'records': records_affected,
                'error': error_message
            })
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to log update: {str(e)}")

def insert_stock_basic_info(engine, info, stock_code, stock_name):
    """插入股票基本信息"""
    try:
        # 转换上市日期从时间戳到日期格式
        listing_timestamp = info.get('firstTradeDateEpochUtc')
        listing_date = None
        if listing_timestamp:
            try:
                listing_date = datetime.fromtimestamp(listing_timestamp).date()
            except (ValueError, TypeError):
                logger.warning(f"无法解析上市日期时间戳: {listing_timestamp}")

        data = {
            'stock_code': stock_code,
            'stock_name': stock_name,
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'company_name_en': info.get('longName'),
            'description': info.get('longBusinessSummary'),
            'address': f"{info.get('address1', '')} {info.get('address2', '')}",
            'website': info.get('website'),
            'employees': info.get('fullTimeEmployees'),
            'listing_date': listing_date
        }
        
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO stocks 
                (stock_code, stock_name, sector, industry, company_name_en, description, 
                address, website, employees, listing_date)
                VALUES 
                (:stock_code, :stock_name, :sector, :industry, :company_name_en, :description,
                :address, :website, :employees, :listing_date)
                ON DUPLICATE KEY UPDATE
                sector=:sector, industry=:industry, company_name_en=:company_name_en,
                description=:description, address=:address, website=:website,
                employees=:employees, listing_date=:listing_date
            """), data)
            conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error inserting stock basic info for {stock_code}: {str(e)}")
        return False

def insert_metrics(engine, data, table_name):
    """单条插入指标数据"""
    try:
        # 过滤掉所有值为 None 的记录
        if not any(v is not None for k, v in data.items() if k != 'stock_code' and k not in ['date', 'report_date']):
            return True

        columns = list(data.keys())
        column_names = ', '.join(columns)
        placeholders = ', '.join([':' + col for col in columns])
        update_stmt = ', '.join([f"{col}=:{col}" for col in columns if col != 'stock_code'])
        
        sql = f"""
            INSERT INTO {table_name} ({column_names})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE
            {update_stmt}
        """
        
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text(sql), data)
        return True
    except Exception as e:
        logger.error(f"Error inserting into {table_name}: {str(e)}")
        return False

def should_update_financial_health(engine, stock_code, current_date):
    """检查是否需要更新财务健康指标"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT MAX(report_date) 
                FROM financial_health 
                WHERE stock_code = :stock_code
            """), {'stock_code': stock_code}).scalar()
            
            if result is None:
                return True  # 没有数据，需更新
            
            last_update = result
            days_diff = (current_date - last_update).days
            
            # 如果超过90天（一个季度）没更新，则更新
            return days_diff >= 90
            
    except Exception as e:
        logger.error(f"检查财务健康更新状态时出错: {str(e)}")
        return False  # 出错时保守处理，不更新 

def ensure_stock_exists(engine, stock_code, stock_name):
    """确保股票基本信息存在"""
    try:
        with engine.connect() as conn:
            # 检查股票是否存在
            result = conn.execute(text(
                "SELECT 1 FROM stocks WHERE stock_code = :code"
            ), {'code': stock_code}).scalar()
            
            # 如果不存在，插入基本信息
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

def process_metric_file(task):
    """处理单个指标文件"""
    file_path, config, engine, counter = task
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 确保股票基本信息存在
            stock_code = data.get('stock_code')
            stock_name = data.get('stock_name')
            if not ensure_stock_exists(engine, stock_code, stock_name):
                return False
                
            # 只保留表中定义的字段
            table_fields = {
                'fundamental_metrics': [
                    'stock_code', 'date', 'pe_ratio', 'pb_ratio', 'roe',
                    'revenue_growth', 'earnings_growth', 'gross_margin', 
                    'operating_margin', 'dividend_yield'
                ],
                'technical_metrics': [
                    'stock_code', 'date', 'current_price', 'high_52week',
                    'low_52week', 'volume', 'avg_volume', 'avg_volume_10d',
                    'ma_200', 'beta'
                ],
                'financial_health': [
                    'stock_code', 'report_date', 'quick_ratio', 'current_ratio',
                    'cash_ratio', 'debt_to_equity', 'interest_coverage',
                    'operating_cash_flow', 'cash_flow_coverage'
                ],
                'industry_metrics': [
                    'stock_code', 'date', 'profit_margin', 'price_to_sales',
                    'industry_rank'
                ],
                'investor_metrics': [
                    'stock_code', 'date', 'insider_holding', 'institution_holding'
                ]
            }
            
            table_name = config['table']
            if table_name in table_fields:
                filtered_data = {k: data.get(k) for k in table_fields[table_name]}
            else:
                filtered_data = data
            
            # 插入数据
            if insert_metrics(engine, filtered_data, table_name):
                counter.increment()
                return True
            
        return False
    except Exception as e:
        logger.error(f"处理文件 {file_path} 时出错: {str(e)}")
        return False

def import_analyzed_data(date_str=None, full_history=False, max_workers=10):
    """从分析结果导入数据到数据库"""
    engine = get_db_engine()
    start_time = datetime.now()
    
    # 1. 先处理股票基本信息
    logger.info("开始导入股票基本信息...")
    for file_path in glob.glob('stock_fundamental/stock_info/**/*_info.json', recursive=True):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            stock_code = data.get('stock_code')
            stock_name = data.get('stock_name')
            if stock_code and stock_name:
                insert_stock_basic_info(engine, data, stock_code, stock_name)
    
    # 2. 再处理指标数据
    analysis_dir = 'stock_fundamental/stock_analysis'
    if not os.path.exists(analysis_dir):
        logger.error("未找到分析结果目录")
        return

    # 获取要处理的日期列表
    if full_history:
        dates = sorted([d for d in os.listdir(analysis_dir) if d[0].isdigit()])
    elif date_str:
        dates = [date_str] if os.path.exists(os.path.join(analysis_dir, date_str)) else []
    else:
        dates = sorted([d for d in os.listdir(analysis_dir) if d[0].isdigit()])
        dates = dates[-1:] if dates else []

    total_success = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for date_dir in dates:
            logger.info(f"\n处理 {date_dir} 的数据...")
            date_path = os.path.join(analysis_dir, date_dir)
            
            # 遍每个板块
            sectors = [s for s in os.listdir(date_path) if os.path.isdir(os.path.join(date_path, s))]
            for sector_idx, sector in enumerate(sectors, 1):
                sector_path = os.path.join(date_path, sector)
                sector_counter = Counter()
                logger.info(f"\n处理板块 [{sector_idx}/{len(sectors)}] {sector}...")
                
                # 处理每种指标
                metrics_map = {
                    'fundamental': {
                        'table': 'fundamental_metrics',
                        'fields': ['stock_code', 'date', 'pe_ratio', 'pb_ratio', 'roe', 
                                  'revenue_growth', 'earnings_growth', 'gross_margin', 
                                  'operating_margin']
                    },
                    'technical': {
                        'table': 'technical_metrics',
                        'fields': ['stock_code', 'date', 'current_price', 'high_52week', 
                                  'low_52week', 'volume', 'avg_volume', 'avg_volume_10d', 
                                  'ma_200']
                    },
                    'financial': {
                        'table': 'financial_health',
                        'fields': ['stock_code', 'report_date', 'quick_ratio', 'current_ratio',
                                  'cash_ratio', 'debt_to_equity', 'interest_coverage',
                                  'operating_cash_flow', 'cash_flow_coverage']
                    },
                    'industry': {
                        'table': 'industry_metrics',
                        'fields': ['stock_code', 'date', 'profit_margin', 'price_to_sales',
                                  'industry_rank']
                    },
                    'investor': {
                        'table': 'investor_metrics',
                        'fields': ['stock_code', 'date', 'insider_holding', 
                                  'institution_holding']
                    }
                }
                
                for metric_type, config in metrics_map.items():
                    metric_dir = os.path.join(sector_path, metric_type)
                    if not os.path.exists(metric_dir):
                        continue
                    
                    files = [f for f in os.listdir(metric_dir) if f.endswith('.json')]
                    logger.info(f"处理 {metric_type} 指标，共 {len(files)} 个文件...")
                    
                    # 准备任务列表
                    tasks = [
                        (os.path.join(metric_dir, file), config, engine, sector_counter)
                        for file in files
                    ]
                    
                    # 并发处理文件
                    futures = [executor.submit(process_metric_file, task) for task in tasks]
                    success_count = sum(1 for future in concurrent.futures.as_completed(futures) if future.result())
                    
                    logger.info(f"{metric_type} 指标处理完成: {success_count}/{len(files)}")
                
                sector_success = sector_counter.value
                total_success += sector_success
                logger.info(f"\n{sector} 板块处理完成: {sector_success} 条记录入库成功")

    # 记录更新日志
    status = 'SUCCESS' if total_success > 0 else 'FAILED'
    log_update(engine, 'all_tables', 'FULL', start_time, status, total_success)
    
    end_time = datetime.now()
    logger.info(f"\n数据导入完成!")
    logger.info(f"总成功: {total_success} 条记录")
    logger.info(f"总耗时: {end_time - start_time}")
    return total_success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='股票数据入库程序')
    parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--full', action='store_true', help='处理所有历史数据')
    parser.add_argument('--workers', type=int, default=10, help='并发工作线程数')
    args = parser.parse_args()

    logger.info("开始导入分析数据...")
    import_analyzed_data(args.date, args.full, args.workers)