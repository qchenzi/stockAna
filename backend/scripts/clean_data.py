from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import sys
import argparse
import logging
sys.path.append('.')
from config.database import DB_CONFIG_ADMIN
from sh_stock_db import get_db_engine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_admin_engine():
    """创建管理员数据库连接引擎"""
    connection_str = (
        f"mysql+pymysql://{DB_CONFIG_ADMIN['user']}:{DB_CONFIG_ADMIN['password']}@"
        f"{DB_CONFIG_ADMIN['host']}/{DB_CONFIG_ADMIN['database']}?charset=utf8mb4"
    )
    try:
        engine = create_engine(connection_str)
        return engine
    except SQLAlchemyError as e:
        logger.error(f"数据库连接失败: {str(e)}")
        raise

def clean_data(date_str=None, clean_all=False):
    """清理数据
    Args:
        date_str: 指定日期，格式为 'YYYY-MM-DD'
        clean_all: 是否清理所有数据
    """
    engine = get_admin_engine()  # 使用管理员引擎
    
    try:
        with engine.connect() as conn:
            with conn.begin():
                if clean_all:
                    # 清理所有数据（保留stocks表的基本信息）
                    tables = [
                        'investor_metrics',
                        'industry_metrics',
                        'technical_metrics',
                        'fundamental_metrics',
                        'financial_health',
                        'update_logs'
                    ]
                    for table in tables:
                        conn.execute(text(f"TRUNCATE TABLE {table}"))
                    print("已清理所有历史数据")
                    
                elif date_str:
                    # 清理指定日期的数据
                    conn.execute(text("DELETE FROM investor_metrics WHERE date = :clean_date"), 
                               {"clean_date": date_str})
                    conn.execute(text("DELETE FROM industry_metrics WHERE date = :clean_date"), 
                               {"clean_date": date_str})
                    conn.execute(text("DELETE FROM technical_metrics WHERE date = :clean_date"), 
                               {"clean_date": date_str})
                    conn.execute(text("DELETE FROM fundamental_metrics WHERE date = :clean_date"), 
                               {"clean_date": date_str})
                    conn.execute(text("DELETE FROM financial_health WHERE report_date = :clean_date"), 
                               {"clean_date": date_str})
                    conn.execute(text("DELETE FROM update_logs WHERE DATE(start_time) = :clean_date"), 
                               {"clean_date": date_str})
                    print(f"成功清理 {date_str} 的数据")
                else:
                    print("请指定要清理的日期或使用 --all 参数清理所有数据")
                    
    except Exception as e:
        print(f"清理数据时出错: {str(e)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='数据清理程序')
    parser.add_argument('--date', help='指定要清理的日期 (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='清理所有历史数据')
    args = parser.parse_args()

    if args.all:
        response = input("警告：这将清理所有历史数据！是否继续？(y/N): ")
        if response.lower() == 'y':
            clean_data(clean_all=True)
    else:
        clean_data(args.date) 