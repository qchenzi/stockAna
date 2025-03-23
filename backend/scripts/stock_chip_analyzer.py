import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.database import DB_CONFIG_ADMIN

from sqlalchemy import create_engine, text
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建数据库连接
engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG_ADMIN['user']}:{DB_CONFIG_ADMIN['password']}"
    f"@{DB_CONFIG_ADMIN['host']}/{DB_CONFIG_ADMIN['database']}?charset=utf8mb4"
)

def get_base_chip_sql():
    """返回基础的筹码计算SQL"""
    return """
    WITH price_data AS (
        -- 计算最近 60 天的技术指标
        SELECT 
            stock_code,
            trade_date,
            close_price,
            high_price,
            low_price,
            volume,
            -- 计算 60 日均线 (MA60)
            AVG(close_price) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ) AS ma60,
            -- 计算 60 日均量
            AVG(volume) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ) AS avg_vol_60d,
            -- 计算 VWAP
            SUM(close_price * volume) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ) / NULLIF(SUM(volume) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ), 0) AS vwap
        FROM stock_historical_quotes
        WHERE trade_date >= DATE_SUB(:latest_date, INTERVAL 60 DAY)
    ),
    chip_distribution AS (
        -- 计算筹码分布
        SELECT 
            stock_code,
            trade_date,
            close_price,
            ma60, vwap, avg_vol_60d,
            -- 计算获利筹码
            SUM(CASE WHEN close_price > vwap THEN volume ELSE 0 END) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ) / NULLIF(SUM(volume) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ), 0) AS profit_chip_ratio,
            -- 计算套牢筹码
            SUM(CASE WHEN close_price < vwap THEN volume ELSE 0 END) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ) / NULLIF(SUM(volume) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ), 0) AS locked_chip_ratio,
            -- 计算主力筹码
            SUM(CASE WHEN volume > 1.2 * avg_vol_60d 
                     AND close_price BETWEEN vwap * 0.98 AND vwap * 1.02
                THEN volume ELSE 0 END) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ) / NULLIF(SUM(volume) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ), 0) AS main_chip_ratio,
            -- 计算浮动筹码
            SUM(CASE WHEN volume < 0.8 * avg_vol_60d THEN volume ELSE 0 END) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ) / NULLIF(SUM(volume) OVER (
                PARTITION BY stock_code ORDER BY trade_date 
                ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
            ), 0) AS floating_chip_ratio
        FROM price_data
    ),
    latest_data AS (
        -- 获取最新数据
        SELECT 
            cd.*,
            s.stock_name,
            s.industry
        FROM chip_distribution cd
        JOIN stocks s ON cd.stock_code = s.stock_code
        WHERE cd.trade_date = :latest_date
    )
    """

def update_chip_analysis():
    """每日更新股票筹码分析"""
    try:
        with engine.connect() as conn:
            # 1. 获取最新交易日期
            date_sql = "SELECT MAX(trade_date) as latest_date FROM stock_historical_quotes"
            latest_date = conn.execute(text(date_sql)).scalar()
            logger.info(f"最新交易日期: {latest_date}")

            if not latest_date:
                logger.error("未找到任何交易数据")
                return False

            # 2. 检查数据完整性
            check_data_sql = """
            SELECT COUNT(DISTINCT stock_code) as stock_count,
                   MIN(trade_date) as earliest_date
            FROM stock_historical_quotes
            WHERE trade_date <= :latest_date
            """
            data_check = conn.execute(text(check_data_sql), 
                                    {'latest_date': latest_date}).first()
            
            if not data_check.stock_count:
                logger.error("数据库中没有足够的历史数据")
                return False

            logger.info(f"数据范围: {data_check.earliest_date} 至 {latest_date}")
            logger.info(f"股票数量: {data_check.stock_count}")

            # 3. 检查是否已存在今日分析
            check_sql = """
            SELECT COUNT(*) 
            FROM stock_chip_analysis 
            WHERE analysis_date = :date
            """
            existing_count = conn.execute(text(check_sql), 
                                       {'date': latest_date}).scalar()
            
            if existing_count > 0:
                logger.info("今日筹码分析已存在，无需重新生成")
                return False

            # 4. 删除当天的历史数据（以防万一）
            conn.execute(text("""
                DELETE FROM stock_chip_analysis 
                WHERE analysis_date = :date
            """), {'date': latest_date})

            base_sql = get_base_chip_sql()

            # 5. 执行低吸策略分析
            logger.info("执行低吸策略分析...")
            low_buy_sql = """
            INSERT INTO stock_chip_analysis (
                stock_code, stock_name, industry, analysis_date, strategy_type, 
                close_price, ma60, vwap, profit_chip_ratio, locked_chip_ratio,
                main_chip_ratio, floating_chip_ratio, rank_num
            )
            WITH price_data AS (
                -- 计算最近 60 天的技术指标
                SELECT 
                    stock_code,
                    trade_date,
                    close_price,
                    high_price,
                    low_price,
                    volume,
                    -- 计算 60 日均线 (MA60)
                    AVG(close_price) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) AS ma60,
                    -- 计算 60 日均量
                    AVG(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) AS avg_vol_60d,
                    -- 计算 VWAP
                    SUM(close_price * volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS vwap
                FROM stock_historical_quotes
                WHERE trade_date >= DATE_SUB(:latest_date, INTERVAL 60 DAY)
            ),
            chip_distribution AS (
                -- 计算筹码分布
                SELECT 
                    stock_code,
                    trade_date,
                    close_price,
                    ma60, vwap, avg_vol_60d,
                    -- 计算获利筹码
                    SUM(CASE WHEN close_price > vwap THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS profit_chip_ratio,
                    -- 计算套牢筹码
                    SUM(CASE WHEN close_price < vwap THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS locked_chip_ratio,
                    -- 计算主力筹码
                    SUM(CASE WHEN volume > 1.2 * avg_vol_60d 
                             AND close_price BETWEEN vwap * 0.98 AND vwap * 1.02
                        THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS main_chip_ratio,
                    -- 计算浮动筹码
                    SUM(CASE WHEN volume < 0.8 * avg_vol_60d THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS floating_chip_ratio
                FROM price_data
            ),
            latest_data AS (
                -- 获取最新数据
                SELECT 
                    cd.*,
                    s.stock_name,
                    s.industry
                FROM chip_distribution cd
                JOIN stocks s ON cd.stock_code = s.stock_code
                WHERE cd.trade_date = :latest_date
            )
            SELECT 
                stock_code, stock_name, industry, :latest_date, '低吸',
                close_price, ma60, vwap, profit_chip_ratio, locked_chip_ratio,
                main_chip_ratio, floating_chip_ratio,
                ROW_NUMBER() OVER (
                    ORDER BY main_chip_ratio DESC, profit_chip_ratio ASC, 
                            ABS(close_price - vwap) ASC
                ) as rank_num
            FROM latest_data
            WHERE main_chip_ratio >= 0.3  -- 主力筹码占比超过30%
            AND profit_chip_ratio < 0.5   -- 获利筹码占比低于50%
            LIMIT 50
            """
            conn.execute(text(low_buy_sql), {'latest_date': latest_date})
            
            # 6. 执行追涨策略分析
            logger.info("执行追涨策略分析...")
            follow_up_sql = """
            INSERT INTO stock_chip_analysis (
                stock_code, stock_name, industry, analysis_date, strategy_type, 
                close_price, ma60, vwap, profit_chip_ratio, locked_chip_ratio,
                main_chip_ratio, floating_chip_ratio, rank_num
            )
            WITH price_data AS (
                -- 计算最近 60 天的技术指标
                SELECT 
                    stock_code,
                    trade_date,
                    close_price,
                    high_price,
                    low_price,
                    volume,
                    AVG(close_price) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) AS ma60,
                    AVG(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) AS avg_vol_60d,
                    SUM(close_price * volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS vwap
                FROM stock_historical_quotes
                WHERE trade_date >= DATE_SUB(:latest_date, INTERVAL 60 DAY)
            ),
            chip_distribution AS (
                -- 计算筹码分布
                SELECT 
                    stock_code,
                    trade_date,
                    close_price,
                    ma60, vwap, avg_vol_60d,
                    -- 计算获利筹码
                    SUM(CASE WHEN close_price > vwap THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS profit_chip_ratio,
                    -- 计算套牢筹码
                    SUM(CASE WHEN close_price < vwap THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS locked_chip_ratio,
                    -- 计算主力筹码
                    SUM(CASE WHEN volume > 1.2 * avg_vol_60d 
                             AND close_price BETWEEN vwap * 0.98 AND vwap * 1.02
                        THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS main_chip_ratio,
                    -- 计算浮动筹码
                    SUM(CASE WHEN volume < 0.8 * avg_vol_60d THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS floating_chip_ratio
                FROM price_data
            ),
            latest_data AS (
                -- 获取最新数据
                SELECT 
                    cd.*,
                    s.stock_name,
                    s.industry
                FROM chip_distribution cd
                JOIN stocks s ON cd.stock_code = s.stock_code
                WHERE cd.trade_date = :latest_date
            )
            SELECT 
                stock_code, stock_name, industry, :latest_date, '追涨',
                close_price, ma60, vwap, profit_chip_ratio, locked_chip_ratio,
                main_chip_ratio, floating_chip_ratio,
                ROW_NUMBER() OVER (
                    ORDER BY 
                        -- 调整排序权重
                        profit_chip_ratio * 0.4 +    -- 获利筹码权重
                        main_chip_ratio * 0.4 +      -- 主力筹码权重
                        (1 - floating_chip_ratio) * 0.2  -- 浮动筹码反向权重
                    DESC
                ) as rank_num
            FROM latest_data
            WHERE 
                -- 放宽筛选条件
                profit_chip_ratio >= 0.6   -- 获利筹码比例降至60%
                AND main_chip_ratio >= 0.3  -- 主力筹码比例降至30%
                AND floating_chip_ratio < 0.4  -- 浮动筹码比例放宽到40%
                AND close_price > ma60  -- 确保价格在60日均线上方
                AND close_price > vwap  -- 确保价格在成本线上方
                AND locked_chip_ratio < 0.3  -- 套牢筹码比例低于30%
            LIMIT 50
            """
            conn.execute(text(follow_up_sql), {'latest_date': latest_date})

            # 7. 执行潜力股策略分析
            logger.info("执行潜力股策略分析...")
            potential_sql = """
            INSERT INTO stock_chip_analysis (
                stock_code, stock_name, industry, analysis_date, strategy_type, 
                close_price, ma60, vwap, profit_chip_ratio, locked_chip_ratio,
                main_chip_ratio, floating_chip_ratio, rank_num
            )
            WITH price_data AS (
                -- 计算最近 60 天的技术指标
                SELECT 
                    stock_code,
                    trade_date,
                    close_price,
                    high_price,
                    low_price,
                    volume,
                    AVG(close_price) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) AS ma60,
                    AVG(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) AS avg_vol_60d,
                    SUM(close_price * volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS vwap
                FROM stock_historical_quotes
                WHERE trade_date >= DATE_SUB(:latest_date, INTERVAL 60 DAY)
            ),
            chip_distribution AS (
                -- 计算筹码分布
                SELECT 
                    stock_code,
                    trade_date,
                    close_price,
                    ma60, vwap, avg_vol_60d,
                    -- 计算获利筹码
                    SUM(CASE WHEN close_price > vwap THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS profit_chip_ratio,
                    -- 计算套牢筹码
                    SUM(CASE WHEN close_price < vwap THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS locked_chip_ratio,
                    -- 计算主力筹码
                    SUM(CASE WHEN volume > 1.2 * avg_vol_60d 
                             AND close_price BETWEEN vwap * 0.98 AND vwap * 1.02
                        THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS main_chip_ratio,
                    -- 计算浮动筹码
                    SUM(CASE WHEN volume < 0.8 * avg_vol_60d THEN volume ELSE 0 END) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ) / NULLIF(SUM(volume) OVER (
                        PARTITION BY stock_code ORDER BY trade_date 
                        ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                    ), 0) AS floating_chip_ratio
                FROM price_data
            ),
            latest_data AS (
                -- 获取最新数据
                SELECT 
                    cd.*,
                    s.stock_name,
                    s.industry
                FROM chip_distribution cd
                JOIN stocks s ON cd.stock_code = s.stock_code
                WHERE cd.trade_date = :latest_date
            )
            SELECT 
                stock_code, stock_name, industry, :latest_date, '潜力',
                close_price, ma60, vwap, profit_chip_ratio, locked_chip_ratio,
                main_chip_ratio, floating_chip_ratio,
                ROW_NUMBER() OVER (
                    ORDER BY main_chip_ratio DESC, floating_chip_ratio ASC, 
                            profit_chip_ratio ASC
                ) as rank_num
            FROM latest_data
            WHERE main_chip_ratio >= 0.5      -- 主力筹码占比超过50%
            AND floating_chip_ratio < 0.3     -- 浮动筹码占比低于30%
            AND profit_chip_ratio BETWEEN 0.6 AND 0.85  -- 获利筹码在合理区间
            LIMIT 50
            """
            conn.execute(text(potential_sql), {'latest_date': latest_date})

            conn.commit()
            logger.info("成功更新筹码分析")
            return True
            
    except Exception as e:
        logger.error(f"更新筹码分析失败: {str(e)}")
        return False

if __name__ == '__main__':
    update_chip_analysis() 