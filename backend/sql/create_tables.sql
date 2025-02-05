-- 创建数据库
CREATE DATABASE IF NOT EXISTS stock_analysis DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE stock_analysis;

-- 1. 股票基本信息表
CREATE TABLE stocks (
    stock_code VARCHAR(6) PRIMARY KEY,
    stock_name VARCHAR(50) NOT NULL,
    sector VARCHAR(50),
    industry VARCHAR(100),
    company_name_en VARCHAR(200),
    description TEXT,
    address VARCHAR(200),
    website VARCHAR(100),
    employees INT,
    listing_date DATE,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. 股票历史交易数据表
CREATE TABLE `stock_historical_quotes` (
  `stock_code` varchar(6) NOT NULL COMMENT '股票代码',
  `trade_date` date NOT NULL COMMENT '交易日期',
  `open_price` decimal(10,2) NOT NULL COMMENT '开盘价',
  `close_price` decimal(10,2) NOT NULL COMMENT '收盘价',
  `high_price` decimal(10,2) NOT NULL COMMENT '最高价',
  `low_price` decimal(10,2) NOT NULL COMMENT '最低价',
  `volume` bigint NOT NULL COMMENT '成交量',
  `amount` decimal(20,2) NOT NULL DEFAULT '0.00' COMMENT '成交额',
  `dividends` decimal(10,4) DEFAULT '0.0000' COMMENT '分红',
  `stock_splits` decimal(10,4) DEFAULT '1.0000' COMMENT '拆股比例',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `amplitude` decimal(10,2) DEFAULT NULL COMMENT '振幅(%)',
  `change_ratio` decimal(10,2) DEFAULT NULL COMMENT '涨跌幅(%)',
  `change_amount` decimal(10,2) DEFAULT NULL COMMENT '涨跌额',
  `turnover_ratio` decimal(10,2) DEFAULT NULL COMMENT '换手率(%)',
  `source` varchar(10) DEFAULT NULL COMMENT '数据来源(yfinance/akshare)',
  `adjust_type` varchar(10) DEFAULT NULL COMMENT '复权类型(qfq/hfq/none)',
  PRIMARY KEY (`stock_code`,`trade_date`),
  KEY `idx_stock_code` (`stock_code`),
  KEY `idx_stock_change` (`stock_code`,`change_ratio`),
  CONSTRAINT `stock_historical_quotes_ibfk_1` FOREIGN KEY (`stock_code`) REFERENCES `stocks` (`stock_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票历史交易数据'


-- 3. 基本面指标表
CREATE TABLE fundamental_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(6),
    date DATE,
    pe_ratio DECIMAL(10,2),
    pb_ratio DECIMAL(10,2),
    roe DECIMAL(10,2),
    revenue_growth DECIMAL(10,2),
    earnings_growth DECIMAL(10,2),
    gross_margin DECIMAL(10,2),
    operating_margin DECIMAL(10,2),
    dividend_yield DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code),
    UNIQUE KEY uk_stock_date (stock_code, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. 技术面指标表
CREATE TABLE technical_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(6),
    date DATE,
    current_price DECIMAL(10,2),
    high_52week DECIMAL(10,2),
    low_52week DECIMAL(10,2),
    volume BIGINT,
    avg_volume BIGINT,
    avg_volume_10d BIGINT,
    ma_200 DECIMAL(10,2),
    beta DECIMAL(10,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code),
    UNIQUE KEY uk_stock_date (stock_code, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. 财务健康指标表
CREATE TABLE financial_health (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(6),
    report_date DATE,
    quick_ratio DECIMAL(10,2),
    current_ratio DECIMAL(10,2),
    cash_ratio DECIMAL(10,2),
    debt_to_equity DECIMAL(10,2),
    interest_coverage DECIMAL(10,2),
    operating_cash_flow DECIMAL(15,2),
    cash_flow_coverage DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code),
    UNIQUE KEY uk_stock_report (stock_code, report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. 行业指标表
CREATE TABLE industry_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(6),
    date DATE,
    profit_margin DECIMAL(10,2),
    price_to_sales DECIMAL(10,2),
    industry_rank INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code),
    UNIQUE KEY uk_stock_date (stock_code, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. 投资者行为表
CREATE TABLE investor_metrics (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(6),
    date DATE,
    insider_holding DECIMAL(10,2),
    institution_holding DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code),
    UNIQUE KEY uk_stock_date (stock_code, date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. 公司高管信息表
CREATE TABLE company_officers (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(6),
    name VARCHAR(100),
    title VARCHAR(100),
    age INT,
    since_date DATE,
    FOREIGN KEY (stock_code) REFERENCES stocks(stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. 数据更新日志表
CREATE TABLE update_logs (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    table_name VARCHAR(50),
    update_type VARCHAR(20),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status VARCHAR(20),
    records_affected INT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 创建索引
CREATE INDEX idx_stock_sector ON stocks(sector);
CREATE INDEX idx_stock_industry ON stocks(industry);
CREATE INDEX idx_fundamental_date ON fundamental_metrics(date);
CREATE INDEX idx_technical_date ON technical_metrics(date);
CREATE INDEX idx_financial_report_date ON financial_health(report_date);
CREATE INDEX idx_industry_date ON industry_metrics(date);
CREATE INDEX idx_investor_date ON investor_metrics(date);
CREATE INDEX idx_update_logs_table ON update_logs(table_name); 


-- 10. 股票推荐表
CREATE TABLE stock_recommendations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    recommend_date DATE NOT NULL COMMENT '推荐日期',
    stock_code VARCHAR(6) NOT NULL COMMENT '股票代码',
    stock_name VARCHAR(50) NOT NULL COMMENT '股票名称',
    industry VARCHAR(100) COMMENT '所属行业',
    current_price DECIMAL(10,2) COMMENT '当前价格',
    total_score INT COMMENT '综合评分',
    recommendation_level VARCHAR(20) COMMENT '推荐等级',
    reasons TEXT COMMENT '推荐理由',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_date (recommend_date),
    INDEX idx_score (total_score),
    INDEX idx_stock (stock_code),
    CONSTRAINT UNIQUE KEY uk_date_stock (recommend_date, stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票推荐记录表';

-- 11. 股票技术评分表
CREATE TABLE `stock_technical_scores` (
    `id` bigint NOT NULL AUTO_INCREMENT,
    `stock_code` varchar(6) NOT NULL COMMENT '股票代码',
    `score_date` date NOT NULL COMMENT '评分日期',
    `trend_score` int DEFAULT NULL COMMENT '趋势评分',
    `momentum_score` int DEFAULT NULL COMMENT '动量评分',
    `volatility_score` int DEFAULT NULL COMMENT '波动率评分',
    `volume_score` int DEFAULT NULL COMMENT '成交量评分',
    `bollinger_score` int DEFAULT NULL COMMENT '布林带评分',
    `total_score` int DEFAULT NULL COMMENT '总评分',
    `ma5` decimal(10,2) DEFAULT NULL COMMENT '5日均线',
    `ma20` decimal(10,2) DEFAULT NULL COMMENT '20日均线',
    `ma60` decimal(10,2) DEFAULT NULL COMMENT '60日均线',
    `vol_ma5` decimal(20,2) DEFAULT NULL COMMENT '5日均量',
    `vol_ma20` decimal(20,2) DEFAULT NULL COMMENT '20日均量',
    `volatility` decimal(10,4) DEFAULT NULL COMMENT '波动率',
    `boll_upper` decimal(10,2) DEFAULT NULL COMMENT '布林带上轨',
    `boll_lower` decimal(10,2) DEFAULT NULL COMMENT '布林带下轨',
    `macd` decimal(10,2) DEFAULT NULL COMMENT 'MACD值',
    `macd_signal` decimal(10,2) DEFAULT NULL COMMENT 'MACD信号线',
    `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_stock_date` (`stock_code`,`score_date`),
    KEY `idx_date_score` (`score_date`,`total_score`),
    KEY `idx_stock_date` (`stock_code`,`score_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票技术评分表';