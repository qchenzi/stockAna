-- 创建用户并设置权限
-- 1. 管理员用户（完全权限）
CREATE USER 'stock_admin'@'localhost' IDENTIFIED BY 'StockAdmin@123';
GRANT ALL PRIVILEGES ON stock_analysis.* TO 'stock_admin'@'localhost';

-- 2. 应用程序用户（读写权限）
CREATE USER 'stock_app'@'localhost' IDENTIFIED BY 'StockApp@123';
GRANT SELECT, INSERT, UPDATE, DELETE ON stock_analysis.* TO 'stock_app'@'localhost';

-- 3. 只读用户（用于数据分析）
CREATE USER 'stock_reader'@'localhost' IDENTIFIED BY 'StockReader@123';
GRANT SELECT ON stock_analysis.* TO 'stock_reader'@'localhost';

-- 刷新权限
FLUSH PRIVILEGES;
