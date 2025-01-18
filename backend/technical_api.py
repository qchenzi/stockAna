from flask import Blueprint, request, jsonify
from sqlalchemy import text
import logging
from config.database import DB_CONFIG_READER
from sqlalchemy import create_engine

# 创建蓝图
technical_bp = Blueprint('technical', __name__)

# 配置日志
logger = logging.getLogger(__name__)

# 创建数据库连接
engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG_READER['user']}:{DB_CONFIG_READER['password']}"
    f"@{DB_CONFIG_READER['host']}/{DB_CONFIG_READER['database']}?charset=utf8mb4"
)

@technical_bp.route('/ma/<stock_code>', methods=['GET'])
def get_moving_averages(stock_code):
    """获取均线数据"""
    try:
        date = request.args.get('date', type=str)
        if not date:
            return jsonify({'error': '日期不能为空'}), 400
            
        sql = """
        WITH ma_calculation AS (
            SELECT stock_code,
                   trade_date,
                   AVG(close_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 4 PRECEDING) AS ma_5,
                   AVG(close_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 9 PRECEDING) AS ma_10,
                   AVG(close_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 19 PRECEDING) AS ma_20,
                   AVG(close_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 59 PRECEDING) AS ma_60,
                   AVG(close_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 199 PRECEDING) AS ma_200
            FROM stock_historical_quotes
            WHERE stock_code = :code
        )
        SELECT *
        FROM ma_calculation
        WHERE trade_date = :date
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(sql), {'code': stock_code, 'date': date}).fetchone()
            
            if not result:
                return jsonify({'error': '未找到数据'}), 404
                
            return jsonify({
                'stock_code': result.stock_code,
                'trade_date': result.trade_date.strftime('%Y-%m-%d'),
                'ma_5': float(result.ma_5) if result.ma_5 else None,
                'ma_10': float(result.ma_10) if result.ma_10 else None,
                'ma_20': float(result.ma_20) if result.ma_20 else None,
                'ma_60': float(result.ma_60) if result.ma_60 else None,
                'ma_200': float(result.ma_200) if result.ma_200 else None
            })
            
    except Exception as e:
        logger.error(f"获取均线数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@technical_bp.route('/cross/<stock_code>', methods=['GET'])
def get_crossovers(stock_code):
    """获取均线交叉信号"""
    try:
        date = request.args.get('date', type=str)
        if not date:
            return jsonify({'error': '日期不能为空'}), 400
            
        sql = """
        WITH RECURSIVE date_series AS (
            SELECT MIN(trade_date) as date_range_start
            FROM stock_historical_quotes
            WHERE trade_date >= DATE_SUB(:date, INTERVAL 30 DAY)
        ),
        moving_averages AS (
            SELECT 
                stock_code,
                trade_date,
                close_price,
                volume,
                AVG(close_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 4 PRECEDING) AS ma_5,
                AVG(close_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 19 PRECEDING) AS ma_20,
                AVG(volume) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 19 PRECEDING) AS volume_ma20
            FROM stock_historical_quotes
            WHERE stock_code = :code
                AND trade_date >= DATE_SUB(:date, INTERVAL 30 DAY)
        ),
        crossover_analysis AS (
            SELECT 
                m.*,
                LAG(ma_5) OVER (PARTITION BY stock_code ORDER BY trade_date) AS prev_ma_5,
                LAG(ma_20) OVER (PARTITION BY stock_code ORDER BY trade_date) AS prev_ma_20,
                ABS(ma_5 - ma_20) / NULLIF(ma_20, 0) * 100 AS cross_strength,
                (ma_5 - LAG(ma_5, 5) OVER (PARTITION BY stock_code ORDER BY trade_date)) 
                    / NULLIF(LAG(ma_5, 5) OVER (PARTITION BY stock_code ORDER BY trade_date), 0) * 100 AS ma_5_change,
                (ma_20 - LAG(ma_20, 5) OVER (PARTITION BY stock_code ORDER BY trade_date))
                    / NULLIF(LAG(ma_20, 5) OVER (PARTITION BY stock_code ORDER BY trade_date), 0) * 100 AS ma_20_change,
                volume / NULLIF(volume_ma20, 0) AS volume_ratio
            FROM moving_averages m
        )
        SELECT 
            stock_code,
            trade_date,
            close_price,
            ROUND(ma_5, 2) as ma_5,
            ROUND(ma_20, 2) as ma_20,
            ROUND(cross_strength, 2) as cross_strength_pct,
            ROUND(ma_5_change, 2) as ma_5_trend,
            ROUND(ma_20_change, 2) as ma_20_trend,
            ROUND(volume_ratio, 2) as volume_ratio,
            CASE 
                WHEN prev_ma_5 < prev_ma_20 AND ma_5 > ma_20 THEN 
                    CASE
                        WHEN cross_strength >= 1 AND ma_5_change > 0 AND volume_ratio >= 1.5 THEN '强金叉'
                        WHEN cross_strength >= 0.5 AND ma_5_change > 0 THEN '金叉'
                        ELSE '弱金叉'
                    END
                WHEN prev_ma_5 > prev_ma_20 AND ma_5 < ma_20 THEN 
                    CASE
                        WHEN cross_strength >= 1 AND ma_5_change < 0 AND volume_ratio >= 1.5 THEN '强死叉'
                        WHEN cross_strength >= 0.5 AND ma_5_change < 0 THEN '死叉'
                        ELSE '弱死叉'
                    END
                ELSE '无交叉'
            END AS cross_type,
            CASE 
                WHEN cross_strength >= 1 THEN 30
                WHEN cross_strength >= 0.5 THEN 20
                WHEN cross_strength >= 0.3 THEN 10
                ELSE 0
            END +
            CASE 
                WHEN (prev_ma_5 < prev_ma_20 AND ma_5 > ma_20 AND ma_5_change > 0 AND ma_20_change > 0) OR
                     (prev_ma_5 > prev_ma_20 AND ma_5 < ma_20 AND ma_5_change < 0 AND ma_20_change < 0)
                THEN 30
                WHEN (prev_ma_5 < prev_ma_20 AND ma_5 > ma_20 AND ma_5_change > 0) OR
                     (prev_ma_5 > prev_ma_20 AND ma_5 < ma_20 AND ma_5_change < 0)
                THEN 20
                ELSE 10
            END +
            CASE 
                WHEN volume_ratio >= 2 THEN 20
                WHEN volume_ratio >= 1.5 THEN 15
                WHEN volume_ratio >= 1 THEN 10
                ELSE 0
            END +
            CASE 
                WHEN cross_strength <= 3 THEN 20
                WHEN cross_strength <= 5 THEN 15
                WHEN cross_strength <= 8 THEN 10
                ELSE 5
            END AS reliability_score
        FROM crossover_analysis
        WHERE trade_date = :date
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(sql), {'code': stock_code, 'date': date}).fetchone()
            
        if not result:
            return jsonify({'error': '未找到数据'}), 404
            
        return jsonify({
            'stock_code': result.stock_code,
            'trade_date': result.trade_date.strftime('%Y-%m-%d'),
            'ma_5': float(result.ma_5),
            'ma_20': float(result.ma_20),
            'cross_type': result.cross_type,
            'cross_strength': float(result.cross_strength_pct),
            'ma_5_trend': float(result.ma_5_trend),
            'ma_20_trend': float(result.ma_20_trend),
            'volume_ratio': float(result.volume_ratio),
            'reliability_score': int(result.reliability_score)
        })
        
    except Exception as e:
        logger.error(f"获取均线交叉数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@technical_bp.route('/three-bullish/<stock_code>', methods=['GET'])
def get_three_bullish(stock_code):
    """获取三连阳形态"""
    try:
        date = request.args.get('date', type=str)
        if not date:
            return jsonify({'error': '日期不能为空'}), 400
            
        sql = """
        WITH continuous_trading_days AS (
            SELECT 
                a.stock_code,
                a.trade_date as cur_date,
                (
                    SELECT MAX(trade_date) 
                    FROM stock_historical_quotes b 
                    WHERE b.stock_code = a.stock_code
                        AND b.trade_date < a.trade_date
                        AND b.trade_date >= DATE_SUB(a.trade_date, INTERVAL 7 DAY)
                ) as prev_date1,
                (
                    SELECT MAX(trade_date)
                    FROM stock_historical_quotes b
                    WHERE b.stock_code = a.stock_code
                        AND b.trade_date < (
                            SELECT MAX(trade_date)
                            FROM stock_historical_quotes c
                            WHERE c.stock_code = a.stock_code
                                AND c.trade_date < a.trade_date
                                AND c.trade_date >= DATE_SUB(a.trade_date, INTERVAL 7 DAY)
                        )
                        AND b.trade_date >= DATE_SUB(a.trade_date, INTERVAL 7 DAY)
                ) as prev_date2
            FROM stock_historical_quotes a
            WHERE a.stock_code = :code
                AND a.trade_date = :date
            GROUP BY a.stock_code, a.trade_date
        ),
        three_days_data AS (
            SELECT 
                t.stock_code,
                c.trade_date,
                c.open_price,
                c.close_price,
                c.volume,
                p1.open_price as prev1_open,
                p1.close_price as prev1_close,
                p1.volume as prev1_volume,
                p2.open_price as prev2_open,
                p2.close_price as prev2_close,
                p2.volume as prev2_volume,
                ABS(c.close_price - c.open_price) / c.open_price * 100 as today_body,
                ABS(p1.close_price - p1.open_price) / p1.open_price * 100 as prev1_body,
                ABS(p2.close_price - p2.open_price) / p2.open_price * 100 as prev2_body,
                (c.close_price - c.open_price) / c.open_price * 100 as today_gain,
                (p1.close_price - p1.open_price) / p1.open_price * 100 as prev1_gain,
                (p2.close_price - p2.open_price) / p2.open_price * 100 as prev2_gain,
                c.volume / NULLIF(p1.volume, 0) as vol_ratio1,
                p1.volume / NULLIF(p2.volume, 0) as vol_ratio2
            FROM continuous_trading_days t
            JOIN stock_historical_quotes c ON t.stock_code = c.stock_code 
                AND t.cur_date = c.trade_date
            LEFT JOIN stock_historical_quotes p1 ON t.stock_code = p1.stock_code 
                AND t.prev_date1 = p1.trade_date
            LEFT JOIN stock_historical_quotes p2 ON t.stock_code = p2.stock_code 
                AND t.prev_date2 = p2.trade_date
        ),
        three_bullish_analysis AS (
            SELECT 
                *,
                CASE WHEN close_price > open_price THEN 1 ELSE 0 END as today_bullish,
                CASE WHEN prev1_close > prev1_open THEN 1 ELSE 0 END as prev1_bullish,
                CASE WHEN prev2_close > prev2_open THEN 1 ELSE 0 END as prev2_bullish,
                ((close_price - prev2_open) / prev2_open * 100) as total_gain
            FROM three_days_data
        )
        SELECT 
            stock_code,
            trade_date as day3,
            ROUND(today_gain, 2) as day3_gain,
            ROUND(prev1_gain, 2) as day2_gain,
            ROUND(prev2_gain, 2) as day1_gain,
            ROUND(total_gain, 2) as total_gain,
            ROUND(vol_ratio1, 2) as latest_vol_ratio,
            CASE 
                WHEN today_bullish = 1 AND prev1_bullish = 1 AND prev2_bullish = 1 
                THEN '三连阳'
                ELSE '否'
            END as pattern_type,
            CASE 
                WHEN today_body >= 2 AND prev1_body >= 2 AND prev2_body >= 2 THEN 30
                WHEN today_body >= 1 AND prev1_body >= 1 AND prev2_body >= 1 THEN 20
                ELSE 10
            END +
            CASE 
                WHEN total_gain >= 6 THEN 30
                WHEN total_gain >= 4 THEN 20
                WHEN total_gain >= 2 THEN 10
                ELSE 5
            END +
            CASE 
                WHEN today_gain > prev1_gain AND prev1_gain > prev2_gain THEN 20
                WHEN today_gain > prev1_gain OR prev1_gain > prev2_gain THEN 10
                ELSE 5
            END +
            CASE 
                WHEN vol_ratio1 > 1.5 THEN 20
                WHEN vol_ratio1 > 1.2 THEN 15
                WHEN vol_ratio1 > 1 THEN 10
                ELSE 5
            END as reliability_score,
            CASE
                WHEN today_bullish = 1 AND prev1_bullish = 1 AND prev2_bullish = 1 THEN
                    CASE
                        WHEN total_gain >= 6 AND vol_ratio1 > 1.5 THEN '强势三连阳'
                        WHEN total_gain >= 4 AND vol_ratio1 > 1.2 THEN '标准三连阳'
                        ELSE '弱势三连阳'
                    END
                ELSE '非三连阳'
            END as pattern_strength
        FROM three_bullish_analysis
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(sql), {'code': stock_code, 'date': date}).fetchone()
            
        if not result:
            return jsonify({'error': '未找到数据'}), 404
            
        return jsonify({
            'stock_code': result.stock_code,
            'day3': result.day3.strftime('%Y-%m-%d'),
            'day3_gain': float(result.day3_gain),
            'day2_gain': float(result.day2_gain),
            'day1_gain': float(result.day1_gain),
            'total_gain': float(result.total_gain),
            'volume_ratio': float(result.latest_vol_ratio),
            'pattern_type': result.pattern_type,
            'reliability_score': int(result.reliability_score),
            'pattern_strength': result.pattern_strength
        })
        
    except Exception as e:
        logger.error(f"获取三连阳数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@technical_bp.route('/engulfing/<stock_code>', methods=['GET'])
def get_engulfing_pattern(stock_code):
    """获取吞没形态"""
    try:
        date = request.args.get('date', type=str)
        if not date:
            return jsonify({'error': '日期不能为空'}), 400
            
        sql = """
        WITH continuous_trading_days AS (
            SELECT 
                a.stock_code,
                a.trade_date as cur_date,
                MAX(b.trade_date) as prev_date
            FROM stock_historical_quotes a
            LEFT JOIN stock_historical_quotes b ON a.stock_code = b.stock_code
                AND b.trade_date < a.trade_date
                AND b.trade_date >= DATE_SUB(a.trade_date, INTERVAL 7 DAY)
            WHERE a.stock_code = :code
                AND a.trade_date = :date
            GROUP BY a.stock_code, a.trade_date
        ),
        pattern_analysis AS (
            SELECT 
                c.stock_code,
                c.trade_date,
                c.open_price,
                c.close_price,
                c.high_price,
                c.low_price,
                c.volume,
                ABS(c.close_price - c.open_price) AS body_length,
                c.high_price - GREATEST(c.open_price, c.close_price) AS upper_shadow,
                LEAST(c.open_price, c.close_price) - c.low_price AS lower_shadow,
                (c.high_price - c.low_price) / c.low_price * 100 AS price_range,
                c.volume / p.volume AS volume_ratio,
                p.open_price AS prev_open,
                p.close_price AS prev_close,
                p.trade_date AS prev_date,
                CASE WHEN c.close_price > c.open_price THEN 1 ELSE -1 END AS candle_type
            FROM continuous_trading_days t
            JOIN stock_historical_quotes c ON t.stock_code = c.stock_code 
                AND t.cur_date = c.trade_date
            JOIN stock_historical_quotes p ON t.stock_code = p.stock_code 
                AND t.prev_date = p.trade_date
        ),
        reliability_score AS (
            SELECT 
                trade_date,
                stock_code,
                prev_date,
                CASE 
                    WHEN body_length / NULLIF((high_price - low_price), 0) > 0.7 THEN 25
                    WHEN body_length / NULLIF((high_price - low_price), 0) > 0.5 THEN 20
                    WHEN body_length / NULLIF((high_price - low_price), 0) > 0.3 THEN 10
                    ELSE 5
                END +
                CASE 
                    WHEN COALESCE(volume_ratio, 0) > 2 THEN 25
                    WHEN COALESCE(volume_ratio, 0) > 1.5 THEN 20
                    WHEN COALESCE(volume_ratio, 0) > 1 THEN 15
                    ELSE 10
                END +
                CASE 
                    WHEN price_range BETWEEN 2 AND 5 THEN 20
                    WHEN price_range BETWEEN 1 AND 7 THEN 15
                    ELSE 10
                END +
                CASE 
                    WHEN upper_shadow < body_length * 0.3 
                         AND lower_shadow < body_length * 0.3 THEN 15
                    WHEN upper_shadow < body_length * 0.5 
                         AND lower_shadow < body_length * 0.5 THEN 10
                    ELSE 5
                END +
                CASE
                    WHEN prev_close IS NOT NULL
                         AND ((prev_close < prev_open AND close_price > open_price
                              AND open_price < prev_close AND close_price > prev_open)
                          OR (prev_close > prev_open AND close_price < open_price
                              AND open_price > prev_close AND close_price < prev_open))
                    THEN 15
                    ELSE 0
                END AS reliability_score,
                
                CASE
                    WHEN prev_close < prev_open AND close_price > open_price
                         AND open_price < prev_close AND close_price > prev_open
                    THEN 'Bullish'
                    WHEN prev_close > prev_open AND close_price < open_price
                         AND open_price > prev_close AND close_price < prev_open
                    THEN 'Bearish'
                    ELSE NULL
                END AS engulfing_type
            FROM pattern_analysis
        )
        SELECT 
            trade_date,
            stock_code,
            prev_date,
            reliability_score,
            CASE 
                WHEN reliability_score >= 90 THEN '极高'
                WHEN reliability_score >= 80 THEN '很高'
                WHEN reliability_score >= 70 THEN '高'
                WHEN reliability_score >= 60 THEN '中等'
                ELSE '低'
            END AS reliability_level,
            engulfing_type
        FROM reliability_score
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(sql), {'code': stock_code, 'date': date}).fetchone()
            
        if not result:
            return jsonify({'error': '未找到数据'}), 404
            
        return jsonify({
            'stock_code': result.stock_code,
            'current_date': result.trade_date.strftime('%Y-%m-%d'),
            'previous_date': result.prev_date.strftime('%Y-%m-%d') if result.prev_date else None,
            'engulfing_type': result.engulfing_type,
            'reliability': result.reliability_score,
            'reliability_level': result.reliability_level
        })
        
    except Exception as e:
        logger.error(f"获取吞没形态数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@technical_bp.route('/support-resistance/<stock_code>', methods=['GET'])
def get_support_resistance(stock_code):
    """获取支撑位和阻力位"""
    try:
        date = request.args.get('date', type=str)
        if not date:
            return jsonify({'error': '日期不能为空'}), 400
            
        sql = """
        WITH price_levels AS (
            SELECT 
                stock_code,
                trade_date,
                close_price,
                high_price,
                low_price,
                volume,
                MAX(high_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 5 PRECEDING) AS max_price_5d,
                MIN(low_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 5 PRECEDING) AS min_price_5d,
                MAX(high_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 10 PRECEDING) AS max_price_10d,
                MIN(low_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 10 PRECEDING) AS min_price_10d,
                MAX(high_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING) AS max_price_20d,
                MIN(low_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING) AS min_price_20d,
                SUM(close_price * volume) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING) / 
                NULLIF(SUM(volume) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING), 0) AS vwap_20d,
                AVG(volume) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING) AS avg_volume_20d,
                (close_price - LAG(close_price, 20) OVER (PARTITION BY stock_code ORDER BY trade_date)) / 
                NULLIF(LAG(close_price, 20) OVER (PARTITION BY stock_code ORDER BY trade_date), 0) * 100 AS price_change_rate_20d
            FROM stock_historical_quotes
            WHERE stock_code = :code
                AND trade_date >= DATE_SUB(:date, INTERVAL 60 DAY)
        ),
        support_resistance_analysis AS (
            SELECT 
                *,
                CASE 
                    WHEN close_price > vwap_20d THEN '价格偏高'
                    ELSE '价格偏低'
                END AS price_position,
                CASE
                    WHEN low_price >= min_price_20d AND volume > avg_volume_20d * 1.5 THEN '强支撑'
                    WHEN low_price >= min_price_20d THEN '一般支撑'
                    ELSE '弱支撑'
                END AS support_strength,
                CASE
                    WHEN high_price <= max_price_20d AND volume > avg_volume_20d * 1.5 THEN '强阻力'
                    WHEN high_price <= max_price_20d THEN '一般阻力'
                    ELSE '弱阻力'
                END AS resistance_strength,
                CASE
                    WHEN close_price >= (max_price_20d + min_price_20d) / 2 THEN '价格偏上'
                    ELSE '价格偏下'
                END AS price_range_position,
                CASE
                    WHEN volume > avg_volume_20d * 1.5 THEN '放量'
                    WHEN volume < avg_volume_20d * 0.7 THEN '缩量'
                    ELSE '量能一般'
                END AS volume_character,
                (CASE 
                    WHEN close_price <= min_price_5d THEN 30
                    WHEN close_price <= min_price_10d THEN 20
                    WHEN close_price <= min_price_20d THEN 10
                    ELSE 0
                END +
                CASE 
                    WHEN volume > avg_volume_20d * 1.5 THEN 30
                    WHEN volume > avg_volume_20d * 1.2 THEN 20
                    WHEN volume > avg_volume_20d THEN 10
                    ELSE 0
                END +
                CASE 
                    WHEN price_change_rate_20d <= -10 THEN 20
                    WHEN price_change_rate_20d <= -5 THEN 15
                    WHEN price_change_rate_20d <= 0 THEN 10
                    ELSE 5
                END +
                CASE 
                    WHEN ABS(min_price_5d - min_price_20d) / min_price_20d * 100 <= 2 THEN 20
                    WHEN ABS(min_price_5d - min_price_20d) / min_price_20d * 100 <= 5 THEN 15
                    ELSE 10
                END) AS support_reliability_score,
                (CASE 
                    WHEN close_price >= max_price_5d THEN 30
                    WHEN close_price >= max_price_10d THEN 20
                    WHEN close_price >= max_price_20d THEN 10
                    ELSE 0
                END +
                CASE 
                    WHEN volume > avg_volume_20d * 1.5 THEN 30
                    WHEN volume > avg_volume_20d * 1.2 THEN 20
                    WHEN volume > avg_volume_20d THEN 10
                    ELSE 0
                END +
                CASE 
                    WHEN price_change_rate_20d >= 10 THEN 20
                    WHEN price_change_rate_20d >= 5 THEN 15
                    WHEN price_change_rate_20d >= 0 THEN 10
                    ELSE 5
                END +
                CASE 
                    WHEN ABS(max_price_5d - max_price_20d) / max_price_20d * 100 <= 2 THEN 20
                    WHEN ABS(max_price_5d - max_price_20d) / max_price_20d * 100 <= 5 THEN 15
                    ELSE 10
                END) AS resistance_reliability_score
            FROM price_levels
        )
        SELECT 
            stock_code,
            trade_date,
            close_price,
            min_price_5d,
            min_price_10d,
            min_price_20d,
            max_price_5d,
            max_price_10d,
            max_price_20d,
            vwap_20d,
            support_strength,
            resistance_strength,
            price_position,
            price_range_position,
            volume_character,
            CASE 
                WHEN support_reliability_score >= 80 THEN '支撑极强'
                WHEN support_reliability_score >= 60 THEN '支撑较强'
                WHEN support_reliability_score >= 40 THEN '支撑一般'
                ELSE '支撑较弱'
            END as support_reliability,
            CASE 
                WHEN resistance_reliability_score >= 80 THEN '阻力极强'
                WHEN resistance_reliability_score >= 60 THEN '阻力较强'
                WHEN resistance_reliability_score >= 40 THEN '阻力一般'
                ELSE '阻力较弱'
            END as resistance_reliability
        FROM support_resistance_analysis
        WHERE trade_date = :date
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(sql), {'code': stock_code, 'date': date}).fetchone()
            
        if not result:
            return jsonify({'error': '未找到数据'}), 404
            
        return jsonify({
            'stock_code': result.stock_code,
            'trade_date': result.trade_date.strftime('%Y-%m-%d'),
            'support_levels': {
                '5d': float(result.min_price_5d),
                '10d': float(result.min_price_10d),
                '20d': float(result.min_price_20d)
            },
            'resistance_levels': {
                '5d': float(result.max_price_5d),
                '10d': float(result.max_price_10d),
                '20d': float(result.max_price_20d)
            },
            'vwap_20d': float(result.vwap_20d),
            'support_strength': result.support_strength,
            'resistance_strength': result.resistance_strength,
            'price_position': result.price_position,
            'price_range_position': result.price_range_position,
            'volume_character': result.volume_character,
            'support_reliability': result.support_reliability,
            'resistance_reliability': result.resistance_reliability
        })
        
    except Exception as e:
        logger.error(f"获取支撑位和阻力位数据失败: {str(e)}")
        return jsonify({'error': str(e)}), 500