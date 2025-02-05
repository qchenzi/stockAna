from sqlalchemy import create_engine, text
from config.database import DB_CONFIG_ADMIN
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

def update_technical_scores():
    """每日更新股票技术评分，并返回评分前50的股票"""
    try:
        with engine.connect() as conn:
            # 1. 删除当天的历史数据
            conn.execute(text("""
                DELETE FROM stock_technical_scores 
                WHERE DATE(score_date) = CURRENT_DATE
            """))

            # 2. 计算并插入新的评分数据，只取评分前50的股票
            conn.execute(text("""
                INSERT INTO stock_technical_scores (
                    stock_code,
                    score_date,
                    trend_score,
                    momentum_score,
                    volatility_score,
                    volume_score,
                    bollinger_score,
                    total_score,
                    ma5,
                    ma20,
                    ma60,
                    vol_ma5,
                    vol_ma20,
                    volatility,
                    boll_upper,
                    boll_lower,
                    macd,
                    macd_signal,
                    created_at
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
                        -- 计算移动均线
                        AVG(close_price) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        ) AS ma5,
                        AVG(close_price) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) AS ma20,
                        AVG(close_price) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                        ) AS ma60,
                        -- MACD相关指标
                        (2 * close_price + 11 * LAG(close_price, 1) OVER (
                            PARTITION BY stock_code ORDER BY trade_date
                        )) / 13 AS macd_fast,
                        (2 * close_price + 25 * LAG(close_price, 1) OVER (
                            PARTITION BY stock_code ORDER BY trade_date
                        )) / 27 AS macd_slow,
                        -- 成交量均线
                        AVG(volume) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        ) AS vol_ma5,
                        AVG(volume) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) AS vol_ma20,
                        -- 波动率
                        STDDEV(close_price) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) AS volatility,
                        -- 布林带
                        AVG(close_price) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) + (2 * STDDEV(close_price) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        )) AS boll_upper,
                        AVG(close_price) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) - (2 * STDDEV(close_price) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        )) AS boll_lower
                    FROM stock_historical_quotes
                    WHERE trade_date >= DATE_SUB(CURRENT_DATE, INTERVAL 60 DAY)
                ),
                macd_data AS (
                    -- 计算 MACD 和信号线
                    SELECT 
                        stock_code,
                        trade_date,
                        close_price,
                        ma5, ma20, ma60, vol_ma5, vol_ma20, volatility, 
                        boll_upper, boll_lower,
                        (macd_fast - macd_slow) AS macd,
                        AVG(macd_fast - macd_slow) OVER (
                            PARTITION BY stock_code ORDER BY trade_date 
                            ROWS BETWEEN 8 PRECEDING AND CURRENT ROW
                        ) AS macd_signal
                    FROM price_data
                ),
                latest_data AS (
                    -- 获取最新数据
                    SELECT * FROM macd_data md
                    WHERE trade_date = (
                        SELECT MAX(trade_date) 
                        FROM stock_historical_quotes sh 
                        WHERE sh.stock_code = md.stock_code
                    )
                ),
                top_scores AS (
                    -- 计算评分并只选择前50名
                    SELECT 
                        stock_code,
                        trade_date as score_date,
                        -- 趋势评分 (40分)
                        CASE 
                            WHEN ma5 > ma20 AND ma20 > ma60 THEN 40
                            WHEN ma5 > ma20 THEN 30
                            WHEN close_price > ma20 THEN 20
                            ELSE 10
                        END AS trend_score,
                        -- 动量评分 (40分)
                        CASE 
                            WHEN macd > macd_signal AND close_price > ma20 THEN 40
                            WHEN macd > macd_signal THEN 30
                            WHEN close_price < ma20 THEN 20
                            ELSE 10
                        END AS momentum_score,
                        -- 波动率评分 (10分)
                        CASE 
                            WHEN volatility > 2 THEN 10
                            ELSE 5
                        END AS volatility_score,
                        -- 成交量评分 (10分)
                        CASE 
                            WHEN vol_ma5 > vol_ma20 THEN 10
                            ELSE 5
                        END AS volume_score,
                        -- 布林带评分 (10分)
                        CASE 
                            WHEN close_price > boll_upper THEN 5
                            WHEN close_price < boll_lower THEN 10
                            ELSE 0
                        END AS bollinger_score,
                        -- 总分使用已计算的单项评分之和
                        CASE 
                            WHEN ma5 > ma20 AND ma20 > ma60 THEN 40
                            WHEN ma5 > ma20 THEN 30
                            WHEN close_price > ma20 THEN 20
                            ELSE 10
                        END + 
                        CASE 
                            WHEN macd > macd_signal AND close_price > ma20 THEN 40
                            WHEN macd > macd_signal THEN 30
                            WHEN close_price < ma20 THEN 20
                            ELSE 10
                        END +
                        CASE WHEN volatility > 2 THEN 10 ELSE 5 END +
                        CASE WHEN vol_ma5 > vol_ma20 THEN 10 ELSE 5 END +
                        CASE WHEN close_price > boll_upper THEN 5 
                             WHEN close_price < boll_lower THEN 10 
                             ELSE 0 END AS total_score,
                        -- 技术指标
                        ma5, ma20, ma60, vol_ma5, vol_ma20, volatility,
                        boll_upper, boll_lower, macd, macd_signal,
                        CURRENT_TIMESTAMP as created_at
                    FROM latest_data
                    WHERE ma5 IS NOT NULL 
                        AND ma20 IS NOT NULL 
                        AND ma60 IS NOT NULL
                    ORDER BY total_score DESC
                    LIMIT 50
                )
                SELECT * FROM top_scores
            """))
            
            conn.commit()
            logger.info("成功更新技术评分")
            return True
            
    except Exception as e:
        logger.error(f"更新技术评分失败: {str(e)}")
        return False

if __name__ == '__main__':
    update_technical_scores() 