-- 计算均线
WITH RECURSIVE date_series AS (
    -- 获取连续的交易日期范围
    SELECT MIN(trade_date) as date_range_start
    FROM stock_historical_quotes
    WHERE trade_date >= DATE_SUB('2025-01-17', INTERVAL 250 DAY)  -- 为了计算MA200，需要更多历史数据
),
moving_averages AS (
    SELECT 
        stock_code,
        trade_date,
        close_price,
        volume,
        -- 计算各周期均线
        AVG(close_price) OVER (
            PARTITION BY stock_code 
            ORDER BY trade_date 
            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
        ) AS ma_5,
        AVG(close_price) OVER (
            PARTITION BY stock_code 
            ORDER BY trade_date 
            ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
        ) AS ma_10,
        AVG(close_price) OVER (
            PARTITION BY stock_code 
            ORDER BY trade_date 
            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
        ) AS ma_20,
        AVG(close_price) OVER (
            PARTITION BY stock_code 
            ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS ma_60,
        AVG(close_price) OVER (
            PARTITION BY stock_code 
            ORDER BY trade_date 
            ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
        ) AS ma_200
    FROM stock_historical_quotes
    WHERE stock_code = '600519'  -- 指定股票代码
        AND trade_date >= (
            SELECT date_range_start FROM date_series
        )
)
SELECT *
FROM moving_averages
WHERE trade_date = '2025-01-17'  -- 筛选目标日期
ORDER BY trade_date;


-- 改进后的均线交叉计算
WITH RECURSIVE date_series AS (
    -- 获取连续的交易日期范围
    SELECT MIN(trade_date) as date_range_start
    FROM stock_historical_quotes
    WHERE trade_date >= DATE_SUB('2025-01-02', INTERVAL 30 DAY)
),
moving_averages AS (
    SELECT 
        stock_code,
        trade_date,
        close_price,
        volume,
        -- 计算各周期均线
        AVG(close_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 4 PRECEDING) AS ma_5,
        AVG(close_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 19 PRECEDING) AS ma_20,
        -- 计算成交量的20日均线
        AVG(volume) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 19 PRECEDING) AS volume_ma20
    FROM stock_historical_quotes
    WHERE stock_code = '601916'
        AND trade_date >= DATE_SUB('2025-01-02', INTERVAL 30 DAY)
),
crossover_analysis AS (
    SELECT 
        m.*,
        LAG(ma_5) OVER (PARTITION BY stock_code ORDER BY trade_date) AS prev_ma_5,
        LAG(ma_20) OVER (PARTITION BY stock_code ORDER BY trade_date) AS prev_ma_20,
        -- 计算交叉强度指标
        ABS(ma_5 - ma_20) / NULLIF(ma_20, 0) * 100 AS cross_strength,
        -- 计算MA5的5日变化率
        (ma_5 - LAG(ma_5, 5) OVER (PARTITION BY stock_code ORDER BY trade_date)) 
            / NULLIF(LAG(ma_5, 5) OVER (PARTITION BY stock_code ORDER BY trade_date), 0) * 100 AS ma_5_change,
        -- 计算MA20的5日变化率
        (ma_20 - LAG(ma_20, 5) OVER (PARTITION BY stock_code ORDER BY trade_date))
            / NULLIF(LAG(ma_20, 5) OVER (PARTITION BY stock_code ORDER BY trade_date), 0) * 100 AS ma_20_change,
        -- 计算成交量比率
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
    -- 交叉可信度评分（满分100）
    CASE 
        -- 1. 交叉强度（30分）
        WHEN cross_strength >= 1 THEN 30
        WHEN cross_strength >= 0.5 THEN 20
        WHEN cross_strength >= 0.3 THEN 10
        ELSE 0
    END +
    -- 2. 均线趋势（30分）
    CASE 
        WHEN (prev_ma_5 < prev_ma_20 AND ma_5 > ma_20 AND ma_5_change > 0 AND ma_20_change > 0) OR
             (prev_ma_5 > prev_ma_20 AND ma_5 < ma_20 AND ma_5_change < 0 AND ma_20_change < 0)
        THEN 30
        WHEN (prev_ma_5 < prev_ma_20 AND ma_5 > ma_20 AND ma_5_change > 0) OR
             (prev_ma_5 > prev_ma_20 AND ma_5 < ma_20 AND ma_5_change < 0)
        THEN 20
        ELSE 10
    END +
    -- 3. 成交量支撑（20分）
    CASE 
        WHEN volume_ratio >= 2 THEN 20
        WHEN volume_ratio >= 1.5 THEN 15
        WHEN volume_ratio >= 1 THEN 10
        ELSE 0
    END +
    -- 4. 均线距离（20分）
    CASE 
        WHEN cross_strength <= 3 THEN 20
        WHEN cross_strength <= 5 THEN 15
        WHEN cross_strength <= 8 THEN 10
        ELSE 5
    END AS reliability_score
FROM crossover_analysis
WHERE trade_date = '2025-01-02'
ORDER BY trade_date;


-- 改进后的三连阳计算
WITH continuous_trading_days AS (
    -- 先找出连续的交易日
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
    WHERE a.stock_code = '000725'
        AND a.trade_date = '2025-01-17'
    GROUP BY a.stock_code, a.trade_date
),
three_days_data AS (
    SELECT 
        t.stock_code,
        -- 当天数据
        c.trade_date,
        c.open_price,
        c.close_price,
        c.high_price,
        c.low_price,
        c.volume,
        -- 前一天数据
        p1.open_price as prev1_open,
        p1.close_price as prev1_close,
        p1.volume as prev1_volume,
        -- 前两天数据
        p2.open_price as prev2_open,
        p2.close_price as prev2_close,
        p2.volume as prev2_volume,
        -- 计算实体长度（相对于当日价格的百分比）
        ABS(c.close_price - c.open_price) / c.open_price * 100 as today_body,
        ABS(p1.close_price - p1.open_price) / p1.open_price * 100 as prev1_body,
        ABS(p2.close_price - p2.open_price) / p2.open_price * 100 as prev2_body,
        -- 计算涨幅
        (c.close_price - c.open_price) / c.open_price * 100 as today_gain,
        (p1.close_price - p1.open_price) / p1.open_price * 100 as prev1_gain,
        (p2.close_price - p2.open_price) / p2.open_price * 100 as prev2_gain,
        -- 计算成交量变化
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
        -- 判断是否为阳线
        CASE WHEN close_price > open_price THEN 1 ELSE 0 END as today_bullish,
        CASE WHEN prev1_close > prev1_open THEN 1 ELSE 0 END as prev1_bullish,
        CASE WHEN prev2_close > prev2_open THEN 1 ELSE 0 END as prev2_bullish,
        -- 计算三天累计涨幅
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
    -- 三连阳可信度评分（满分100）
    CASE 
        -- 1. 实体强度（30分）
        WHEN today_body >= 2 AND prev1_body >= 2 AND prev2_body >= 2 THEN 30
        WHEN today_body >= 1 AND prev1_body >= 1 AND prev2_body >= 1 THEN 20
        ELSE 10
    END +
    -- 2. 涨幅力度（30分）
    CASE 
        WHEN total_gain >= 6 THEN 30
        WHEN total_gain >= 4 THEN 20
        WHEN total_gain >= 2 THEN 10
        ELSE 5
    END +
    -- 3. 涨幅递增（20分）
    CASE 
        WHEN today_gain > prev1_gain AND prev1_gain > prev2_gain THEN 20
        WHEN today_gain > prev1_gain OR prev1_gain > prev2_gain THEN 10
        ELSE 5
    END +
    -- 4. 成交量配合（20分）
    CASE 
        WHEN vol_ratio1 > 1.5 THEN 20
        WHEN vol_ratio1 > 1.2 THEN 15
        WHEN vol_ratio1 > 1 THEN 10
        ELSE 5
    END as reliability_score,
    -- 形态特征描述
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
WHERE trade_date = '2025-01-17'
ORDER BY reliability_score DESC;


-- 计算吞没形态
-- 查询某只股票在某日期是否出现吞没形态
-- 1. 多头吞没（Bullish Engulfing）
-- 定义
-- 出现位置：通常在下降趋势的尾部，表示可能的趋势反转向上。
-- 形态特征：
-- 前一天是阴线（close_price < open_price）。
-- 当前一天是阳线（close_price > open_price）。
-- 当前一天的开盘价低于前一天的收盘价。
-- 当前一天的收盘价高于前一天的开盘价。
-- 当前阳线完全"吞没"了前一天的阴线。
-- 含义
-- 表示市场由空头主导转向多头主导。
-- 可能是趋势反转信号，预示着股价可能开始上涨。

-- 2. 空头吞没（Bearish Engulfing）
-- 定义
-- 出现位置：通常在上升趋势的尾部，表示可能的趋势反转向下。
-- 形态特征：
-- 前一天是阳线（close_price > open_price）。
-- 当前一天是阴线（close_price < open_price）。
-- 当前一天的开盘价高于前一天的收盘价。
-- 当前一天的收盘价低于前一天的开盘价。
-- 当前阴线完全"吞没"了前一天的阳线。
-- 含义
-- 表示市场由多头主导转向空头主导。
-- 可能是趋势反转信号，预示着股价可能开始下跌。

-- 3. 实战应用
-- 多头吞没的交易策略
-- 买入时机：当多头吞没形态出现在重要的支撑位附近，或者在下降趋势尾部出现时，可能预示着价格反转向上。
-- 止损设置：止损位可以设置在多头吞没形态中阳线的最低点以下。
-- 空头吞没的交易策略
-- 卖出时机：当空头吞没形态出现在重要的阻力位附近，或者在上升趋势尾部出现时，可能预示着价格反转向下。
-- 止损设置：止损位可以设置在空头吞没形态中阴线的最高点以上。

-- 4. 注意事项
-- 形态确认：吞没形态需要结合其他指标（如成交量、趋势线）进行验证，以避免假信号。
-- 市场背景：吞没形态在不同市场背景（如牛市或熊市）中的有效性可能不同。
-- 时间周期：在较长时间周期（如日线或周线）上的吞没形态通常比短时间周期（如分钟线）更可靠。
-- 计算K线形态的可信度
WITH continuous_trading_days AS (
    -- 先找出连续的交易日
    SELECT 
        a.stock_code,
        a.trade_date as cur_date,
        MAX(b.trade_date) as prev_date  -- 找出当前日期之前最近的交易日
    FROM stock_historical_quotes a
    LEFT JOIN stock_historical_quotes b ON a.stock_code = b.stock_code
        AND b.trade_date < a.trade_date  -- 之前的交易日
        AND b.trade_date >= DATE_SUB(a.trade_date, INTERVAL 7 DAY)  -- 限制在7天内查找，提高性能
    WHERE a.stock_code = '688767'
        AND a.trade_date = '2024-01-05'  -- 目标日期
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
        -- 计算实体长度（绝对值）
        ABS(c.close_price - c.open_price) AS body_length,
        -- 计算上影线长度
        c.high_price - GREATEST(c.open_price, c.close_price) AS upper_shadow,
        -- 计算下影线长度
        LEAST(c.open_price, c.close_price) - c.low_price AS lower_shadow,
        -- 计算当日振幅
        (c.high_price - c.low_price) / c.low_price * 100 AS price_range,
        -- 计算成交量变化（使用前一个交易日的数据）
        c.volume / p.volume AS volume_ratio,
        -- 获取前一个交易日数据
        p.open_price AS prev_open,
        p.close_price AS prev_close,
        -- 判断是否为阳线或阴线
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
        -- 基础可信度评分（满分100）
        CASE 
            -- 1. 实体强度（占比25分）
            WHEN body_length / NULLIF((high_price - low_price), 0) > 0.7 THEN 25  -- 添加 NULLIF 避免除零
            WHEN body_length / NULLIF((high_price - low_price), 0) > 0.5 THEN 20
            WHEN body_length / NULLIF((high_price - low_price), 0) > 0.3 THEN 10
            ELSE 5
        END +
        -- 2. 成交量支撑（占比25分）
        CASE 
            WHEN COALESCE(volume_ratio, 0) > 2 THEN 25   -- 添加 COALESCE 处理 NULL
            WHEN COALESCE(volume_ratio, 0) > 1.5 THEN 20
            WHEN COALESCE(volume_ratio, 0) > 1 THEN 15
            ELSE 10
        END +
        -- 3. 价格波动合理性（占比20分）
        CASE 
            WHEN price_range BETWEEN 2 AND 5 THEN 20
            WHEN price_range BETWEEN 1 AND 7 THEN 15
            ELSE 10
        END +
        -- 4. 影线评估（占比15分）
        CASE 
            WHEN upper_shadow < body_length * 0.3 
                 AND lower_shadow < body_length * 0.3 THEN 15
            WHEN upper_shadow < body_length * 0.5 
                 AND lower_shadow < body_length * 0.5 THEN 10
            ELSE 5
        END +
        -- 5. 吞没形态评估（占比15分）
        CASE
            -- 多头吞没
            WHEN prev_close IS NOT NULL  -- 确保有前一天数据
                 AND prev_close < prev_open  -- 前一天阴线
                 AND close_price > open_price  -- 当前阳线
                 AND open_price < prev_close  -- 当前开盘价低于前一天收盘价
                 AND close_price > prev_open  -- 当前收盘价高于前一天开盘价
            THEN 15
            -- 空头吞没
            WHEN prev_close IS NOT NULL  -- 确保有前一天数据
                 AND prev_close > prev_open  -- 前一天阳线
                 AND close_price < open_price  -- 当前阴线
                 AND open_price > prev_close  -- 当前开盘价高于前一天收盘价
                 AND close_price < prev_open  -- 当前收盘价低于前一天开盘价
            THEN 15
            ELSE 0
        END AS reliability_score,
        
        -- 记录具体指标供分析
        body_length,
        upper_shadow,
        lower_shadow,
        price_range,
        volume_ratio,
        candle_type,
        -- 记录吞没形态
        CASE
            WHEN prev_close IS NOT NULL  -- 确保有前一天数据
                 AND prev_close < prev_open 
                 AND close_price > open_price
                 AND open_price < prev_close
                 AND close_price > prev_open
            THEN '多头吞没'
            WHEN prev_close IS NOT NULL  -- 确保有前一天数据
                 AND prev_close > prev_open
                 AND close_price < open_price
                 AND open_price > prev_close
                 AND close_price < prev_open
            THEN '空头吞没'
            ELSE NULL
        END AS engulfing_pattern
    FROM pattern_analysis
)
SELECT 
    trade_date,
    stock_code,
    reliability_score,
    -- 可信度等级
    CASE 
        WHEN reliability_score >= 90 THEN '极高'
        WHEN reliability_score >= 80 THEN '很高'
        WHEN reliability_score >= 70 THEN '高'
        WHEN reliability_score >= 60 THEN '中等'
        ELSE '低'
    END AS reliability_level,
    -- 详细指标
    body_length AS "实体长度",
    upper_shadow AS "上影线长度",
    lower_shadow AS "下影线长度",
    ROUND(price_range, 2) AS "振幅",
    ROUND(COALESCE(volume_ratio, 0), 2) AS "量比",
    CASE candle_type 
        WHEN 1 THEN '阳线'
        ELSE '阴线'
    END AS "K线类型",
    engulfing_pattern AS "吞没形态"
FROM reliability_score
WHERE trade_date = '2024-01-05'  -- 这里改成具体的日期
ORDER BY reliability_score DESC;


-- 计算所有股票在指定日期吞没形态
WITH indexed_trading_days AS (
    SELECT stock_code,
           trade_date,
           close_price,
           open_price,
           ROW_NUMBER() OVER (PARTITION BY stock_code ORDER BY trade_date) AS trade_day_index -- 为每只股票生成交易日索引
    FROM stock_historical_quotes
)
SELECT c.stock_code,
       c.trade_date AS cur_date,
       p.trade_date AS prev_date,
       CASE
           WHEN p.close_price > p.open_price  -- 前一天阳线
                AND c.close_price < c.open_price  -- 当前阴线
                AND c.open_price > p.close_price  -- 当前开盘价高于前一天收盘价
                AND c.close_price < p.open_price  -- 当前收盘价低于前一天开盘价
           THEN '空头吞没'
           WHEN p.close_price < p.open_price  -- 前一天阴线
                AND c.close_price > c.open_price  -- 当前阳线
                AND c.open_price < p.close_price  -- 当前开盘价低于前一天收盘价
                AND c.close_price > p.open_price  -- 当前收盘价高于前一天开盘价
           THEN '多头吞没'
           ELSE NULL
       END AS engulfing_type
FROM indexed_trading_days c
JOIN indexed_trading_days p ON c.stock_code = p.stock_code -- 同一股票
                            AND c.trade_day_index = p.trade_day_index + 1 -- 前一个交易日
WHERE c.trade_date = '2024-12-20' -- 指定目标日期
  AND (p.close_price > p.open_price OR p.close_price < p.open_price); -- 确保有吞没形态


-- 改进后的支撑位和阻力位计算（使用中文描述）
WITH price_levels AS (
    SELECT 
        stock_code,
        trade_date,
        close_price,
        high_price,
        low_price,
        volume,
        -- 计算不同周期的高低点
        MAX(high_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 5 PRECEDING) AS max_price_5d,
        MIN(low_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 5 PRECEDING) AS min_price_5d,
        MAX(high_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 10 PRECEDING) AS max_price_10d,
        MIN(low_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 10 PRECEDING) AS min_price_10d,
        MAX(high_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING) AS max_price_20d,
        MIN(low_price) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING) AS min_price_20d,
        -- 计算成交量加权平均价格(VWAP)
        SUM(close_price * volume) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING) / 
        NULLIF(SUM(volume) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING), 0) AS vwap_20d,
        -- 计算成交量分布
        AVG(volume) OVER (PARTITION BY stock_code ORDER BY trade_date ROWS 20 PRECEDING) AS avg_volume_20d,
        -- 计算价格变化率
        (close_price - LAG(close_price, 20) OVER (PARTITION BY stock_code ORDER BY trade_date)) / 
        NULLIF(LAG(close_price, 20) OVER (PARTITION BY stock_code ORDER BY trade_date), 0) * 100 AS price_change_rate_20d
    FROM stock_historical_quotes
    WHERE stock_code = '600519'
        AND trade_date >= DATE_SUB('2024-01-05', INTERVAL 60 DAY)  -- 获取更多历史数据用于分析
),
support_resistance_analysis AS (
    SELECT 
        *,
        -- 价格位置描述
        CASE 
            WHEN close_price > vwap_20d THEN '高于加权均价'
            ELSE '低于加权均价'
        END AS price_position,
        -- 支撑位强度
        CASE
            WHEN low_price >= min_price_20d AND volume > avg_volume_20d * 1.5 THEN '强支撑'
            WHEN low_price >= min_price_20d THEN '一般支撑'
            ELSE '弱支撑'
        END AS support_strength,
        -- 阻力位强度
        CASE
            WHEN high_price <= max_price_20d AND volume > avg_volume_20d * 1.5 THEN '强阻力'
            WHEN high_price <= max_price_20d THEN '一般阻力'
            ELSE '弱阻力'
        END AS resistance_strength,
        -- 价格区间位置
        CASE
            WHEN close_price >= (max_price_20d + min_price_20d) / 2 THEN '价格区间上半部'
            ELSE '价格区间下半部'
        END AS price_range_position,
        -- 成交量特征
        CASE
            WHEN volume > avg_volume_20d * 1.5 THEN '放量'
            WHEN volume < avg_volume_20d * 0.7 THEN '缩量'
            ELSE '量能一般'
        END AS volume_character,
        -- 计算支撑位可信度评分
        CASE 
            -- 1. 价格位置（30分）
            WHEN close_price <= min_price_5d THEN 30
            WHEN close_price <= min_price_10d THEN 20
            WHEN close_price <= min_price_20d THEN 10
            ELSE 0
        END +
        -- 2. 成交量支撑（30分）
        CASE 
            WHEN volume > avg_volume_20d * 1.5 THEN 30
            WHEN volume > avg_volume_20d * 1.2 THEN 20
            WHEN volume > avg_volume_20d THEN 10
            ELSE 0
        END +
        -- 3. 价格趋势（20分）
        CASE 
            WHEN price_change_rate_20d <= -10 THEN 20  -- 下跌趋势中的支撑更重要
            WHEN price_change_rate_20d <= -5 THEN 15
            WHEN price_change_rate_20d <= 0 THEN 10
            ELSE 5
        END +
        -- 4. 支撑位收敛度（20分）
        CASE 
            WHEN ABS(min_price_5d - min_price_20d) / min_price_20d * 100 <= 2 THEN 20  -- 支撑位密集
            WHEN ABS(min_price_5d - min_price_20d) / min_price_20d * 100 <= 5 THEN 15
            ELSE 10
        END AS support_reliability_score,
        -- 计算阻力位可信度评分
        CASE 
            -- 1. 价格位置（30分）
            WHEN close_price >= max_price_5d THEN 30
            WHEN close_price >= max_price_10d THEN 20
            WHEN close_price >= max_price_20d THEN 10
            ELSE 0
        END +
        -- 2. 成交量阻力（30分）
        CASE 
            WHEN volume > avg_volume_20d * 1.5 THEN 30
            WHEN volume > avg_volume_20d * 1.2 THEN 20
            WHEN volume > avg_volume_20d THEN 10
            ELSE 0
        END +
        -- 3. 价格趋势（20分）
        CASE 
            WHEN price_change_rate_20d >= 10 THEN 20  -- 上涨趋势中的阻力更重要
            WHEN price_change_rate_20d >= 5 THEN 15
            WHEN price_change_rate_20d >= 0 THEN 10
            ELSE 5
        END +
        -- 4. 阻力位收敛度（20分）
        CASE 
            WHEN ABS(max_price_5d - max_price_20d) / max_price_20d * 100 <= 2 THEN 20  -- 阻力位密集
            WHEN ABS(max_price_5d - max_price_20d) / max_price_20d * 100 <= 5 THEN 15
            ELSE 10
        END AS resistance_reliability_score
    FROM price_levels
)
SELECT 
    stock_code as '股票代码',
    trade_date as '交易日期',
    close_price as '收盘价',
    -- 支撑位
    ROUND(min_price_5d, 2) as '5日支撑位',
    ROUND(min_price_10d, 2) as '10日支撑位',
    ROUND(min_price_20d, 2) as '20日支撑位',
    -- 阻力位
    ROUND(max_price_5d, 2) as '5日阻力位',
    ROUND(max_price_10d, 2) as '10日阻力位',
    ROUND(max_price_20d, 2) as '20日阻力位',
    -- VWAP
    ROUND(vwap_20d, 2) as '20日加权均价',
    -- 形态描述
    support_strength as '支撑强度',
    resistance_strength as '阻力强度',
    price_position as '价格位置',
    price_range_position as '区间位置',
    volume_character as '量能特征',
    -- 支撑位可信度评分
    CASE 
        WHEN support_reliability_score >= 80 THEN '支撑极强'
        WHEN support_reliability_score >= 60 THEN '支撑较强'
        WHEN support_reliability_score >= 40 THEN '支撑一般'
        ELSE '支撑较弱'
    END as '支撑可信度',
    -- 阻力位可信度评分
    CASE 
        WHEN resistance_reliability_score >= 80 THEN '阻力极强'
        WHEN resistance_reliability_score >= 60 THEN '阻力较强'
        WHEN resistance_reliability_score >= 40 THEN '阻力一般'
        ELSE '阻力较弱'
    END as '阻力可信度'
FROM support_resistance_analysis
WHERE trade_date = '2024-01-05'
ORDER BY trade_date;