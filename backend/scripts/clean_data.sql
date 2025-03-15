-- 参数设置
SET @clean_date = NULL;  -- 设置为NULL表示清理所有数据，否则设置具体日期，如'2024-12-20'
SET @clean_all = TRUE;   -- 是否清理所有数据

-- 清理数据
BEGIN;

-- 根据参数选择清理方式
IF @clean_all THEN
    -- 清理所有数据（保留stocks表的基本信息）
    TRUNCATE TABLE investor_metrics;
    TRUNCATE TABLE industry_metrics;
    TRUNCATE TABLE technical_metrics;
    TRUNCATE TABLE fundamental_metrics;
    TRUNCATE TABLE financial_health;
    TRUNCATE TABLE update_logs;
    
    SELECT '已清理所有历史数据' as message;
ELSEIF @clean_date IS NOT NULL THEN
    -- 清理指定日期的数据
    DELETE FROM investor_metrics WHERE date = @clean_date;
    DELETE FROM industry_metrics WHERE date = @clean_date;
    DELETE FROM technical_metrics WHERE date = @clean_date;
    DELETE FROM fundamental_metrics WHERE date = @clean_date;
    DELETE FROM financial_health WHERE report_date = @clean_date;
    DELETE FROM update_logs WHERE DATE(start_time) = @clean_date;
    
    SELECT CONCAT('已清理 ', @clean_date, ' 的数据') as message;
ELSE
    SELECT '请设置 @clean_date 或 @clean_all 参数' as message;
END IF;

COMMIT;