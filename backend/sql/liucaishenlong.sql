-- 1. 低吸策略
-- 适用于：想要寻找主力深度控盘、短期回调但有支撑的股票。
-- 主力筹码高 (main_chip_ratio) → 说明主力资金还没出货
-- 获利筹码低 (profit_chip_ratio)  → 说明主力可能还在建仓，而不是高位出货
-- 股价接近 VWAP → 说明股价处于主力成本区，安全性高
-- 浮动筹码低 (floating_chip_ratio) → 说明市场抛压小，股价容易上涨
-- 套牢筹码低 (locked_chip_ratio) → 说明套牢盘少，解套压力小
-- 60日均线向上 (ma60_up) → 说明趋势向上，支撑力强
-- 60日均量向上 (avg_vol_60d_up) → 说明成交量配合良好

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

        -- 计算 VWAP（成交量加权平均成本）
        SUM(close_price * volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS vwap

    FROM stock_historical_quotes
    WHERE trade_date >= DATE_SUB(CURRENT_DATE, INTERVAL 60 DAY)
),

chip_distribution AS (
    -- 计算筹码分布
    SELECT 
        stock_code,
        trade_date,
        close_price,
        ma60, vwap, avg_vol_60d,

        -- 计算获利筹码（股价高于 VWAP）
        SUM(CASE WHEN close_price > vwap THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS profit_chip_ratio,

        -- 计算套牢筹码（股价低于 VWAP）
        SUM(CASE WHEN close_price < vwap THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS locked_chip_ratio,

        -- 计算主力筹码（成交量 > 1.2 * 60日均量，且股价接近 VWAP）
        SUM(CASE WHEN volume > 1.2 * avg_vol_60d 
                 AND close_price BETWEEN vwap * 0.98 AND vwap * 1.02
            THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS main_chip_ratio,

        -- 计算浮动筹码（成交量 < 0.8 * 60日均量）
        SUM(CASE WHEN volume < 0.8 * avg_vol_60d THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS floating_chip_ratio

    FROM price_data
),

latest_data AS (
    -- 获取最新数据
    SELECT * FROM chip_distribution cd
    WHERE trade_date = (
        SELECT MAX(trade_date) 
        FROM stock_historical_quotes sh 
        WHERE sh.stock_code = cd.stock_code
    )
)

SELECT 
    stock_code,
    trade_date AS score_date,
    close_price,
    ma60, vwap,
    profit_chip_ratio AS 获利筹码比例,
    locked_chip_ratio AS 套牢筹码比例,
    main_chip_ratio AS 主力筹码比例,
    floating_chip_ratio AS 浮动筹码比例
FROM latest_data
ORDER BY main_chip_ratio DESC, profit_chip_ratio ASC, ABS(close_price - vwap) ASC
LIMIT 50;


-- 2. 追涨策略
-- 短线交易者，寻找主力控盘高、获利筹码高、股价突破关键压力位的股票。
-- 排序依据：
-- 获利筹码 (profit_chip_ratio) 降序 → 选择市场情绪最乐观的股票
-- 主力筹码 (main_chip_ratio) 降序 → 说明上涨是主力资金推动的
-- 浮动筹码 (floating_chip_ratio) 低 → 说明市场筹码结构稳定，不容易被短线抛压影响
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

        -- 计算 VWAP（成交量加权平均成本）
        SUM(close_price * volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS vwap

    FROM stock_historical_quotes
    WHERE trade_date >= DATE_SUB(CURRENT_DATE, INTERVAL 60 DAY)
),

chip_distribution AS (
    -- 计算筹码分布
    SELECT 
        stock_code,
        trade_date,
        close_price,
        ma60, vwap, avg_vol_60d,

        -- 计算获利筹码（股价高于 VWAP）
        SUM(CASE WHEN close_price > vwap THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS profit_chip_ratio,

        -- 计算套牢筹码（股价低于 VWAP）
        SUM(CASE WHEN close_price < vwap THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS locked_chip_ratio,

        -- 计算主力筹码（成交量 > 1.2 * 60日均量，且股价接近 VWAP）
        SUM(CASE WHEN volume > 1.2 * avg_vol_60d 
                 AND close_price BETWEEN vwap * 0.98 AND vwap * 1.02
            THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS main_chip_ratio,

        -- 计算浮动筹码（成交量 < 0.8 * 60日均量）
        SUM(CASE WHEN volume < 0.8 * avg_vol_60d THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS floating_chip_ratio

    FROM price_data
),

latest_data AS (
    -- 获取最新数据
    SELECT * FROM chip_distribution cd
    WHERE trade_date = (
        SELECT MAX(trade_date) 
        FROM stock_historical_quotes sh 
        WHERE sh.stock_code = cd.stock_code
    )
)

SELECT 
    stock_code,
    trade_date AS score_date,
    close_price,
    ma60, vwap,
    profit_chip_ratio AS 获利筹码比例,
    locked_chip_ratio AS 套牢筹码比例,
    main_chip_ratio AS 主力筹码比例,
    floating_chip_ratio AS 浮动筹码比例
FROM latest_data
ORDER BY profit_chip_ratio DESC, main_chip_ratio DESC, floating_chip_ratio ASC
LIMIT 50;


-- 3. 筹码集中度策略（寻找潜力股）
-- 寻找主力筹码高、浮动筹码低、市值低但有潜力上涨的股票。
-- 主力筹码 (main_chip_ratio) 降序 → 选择筹码最集中的股票
-- 浮动筹码 (floating_chip_ratio) 低 → 说明市场筹码结构稳定
-- 获利筹码 (profit_chip_ratio) 适中（60-85%） → 说明股票上涨仍有空间
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

        -- 计算 VWAP（成交量加权平均成本）
        SUM(close_price * volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS vwap

    FROM stock_historical_quotes
    WHERE trade_date >= DATE_SUB(CURRENT_DATE, INTERVAL 60 DAY)
),

chip_distribution AS (
    -- 计算筹码分布
    SELECT 
        stock_code,
        trade_date,
        close_price,
        ma60, vwap, avg_vol_60d,

        -- 计算获利筹码（股价高于 VWAP）
        SUM(CASE WHEN close_price > vwap THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS profit_chip_ratio,

        -- 计算套牢筹码（股价低于 VWAP）
        SUM(CASE WHEN close_price < vwap THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS locked_chip_ratio,

        -- 计算主力筹码（成交量 > 1.2 * 60日均量，且股价接近 VWAP）
        SUM(CASE WHEN volume > 1.2 * avg_vol_60d 
                 AND close_price BETWEEN vwap * 0.98 AND vwap * 1.02
            THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS main_chip_ratio,

        -- 计算浮动筹码（成交量 < 0.8 * 60日均量）
        SUM(CASE WHEN volume < 0.8 * avg_vol_60d THEN volume ELSE 0 END) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) / SUM(volume) OVER (
            PARTITION BY stock_code ORDER BY trade_date 
            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
        ) AS floating_chip_ratio

    FROM price_data
),

latest_data AS (
    -- 获取最新数据
    SELECT * FROM chip_distribution cd
    WHERE trade_date = (
        SELECT MAX(trade_date) 
        FROM stock_historical_quotes sh 
        WHERE sh.stock_code = cd.stock_code
    )
)

SELECT 
    stock_code,
    trade_date AS score_date,
    close_price,
    ma60, vwap,
    profit_chip_ratio AS 获利筹码比例,
    locked_chip_ratio AS 套牢筹码比例,
    main_chip_ratio AS 主力筹码比例,
    floating_chip_ratio AS 浮动筹码比例
FROM latest_data
ORDER BY main_chip_ratio DESC, floating_chip_ratio ASC, profit_chip_ratio ASC
LIMIT 50;