/*
 Navicat MySQL Dump SQL

 Source Server         : mac
 Source Server Type    : MySQL
 Source Server Version : 80040 (8.0.40)
 Source Host           : 0.0.0.0:3306
 Source Schema         : stock_analysis

 Target Server Type    : MySQL
 Target Server Version : 80040 (8.0.40)
 File Encoding         : 65001

 Date: 15/03/2025 10:45:33
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for company_officers
-- ----------------------------
DROP TABLE IF EXISTS `company_officers`;
CREATE TABLE `company_officers` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `title` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `age` int DEFAULT NULL,
  `since_date` date DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `stock_code` (`stock_code`) USING BTREE,
  CONSTRAINT `company_officers_ibfk_1` FOREIGN KEY (`stock_code`) REFERENCES `stocks` (`stock_code`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for financial_health
-- ----------------------------
DROP TABLE IF EXISTS `financial_health`;
CREATE TABLE `financial_health` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `report_date` date DEFAULT NULL,
  `quick_ratio` decimal(10,2) DEFAULT NULL,
  `current_ratio` decimal(10,2) DEFAULT NULL,
  `cash_ratio` decimal(10,2) DEFAULT NULL,
  `debt_to_equity` decimal(10,2) DEFAULT NULL,
  `interest_coverage` decimal(10,2) DEFAULT NULL,
  `operating_cash_flow` decimal(15,2) DEFAULT NULL,
  `cash_flow_coverage` decimal(10,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_stock_report` (`stock_code`,`report_date`) USING BTREE,
  CONSTRAINT `financial_health_ibfk_1` FOREIGN KEY (`stock_code`) REFERENCES `stocks` (`stock_code`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=241780 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for fundamental_metrics
-- ----------------------------
DROP TABLE IF EXISTS `fundamental_metrics`;
CREATE TABLE `fundamental_metrics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `date` date DEFAULT NULL,
  `pe_ratio` decimal(10,2) DEFAULT NULL,
  `pb_ratio` decimal(10,2) DEFAULT NULL,
  `roe` decimal(10,2) DEFAULT NULL,
  `revenue_growth` decimal(10,2) DEFAULT NULL,
  `earnings_growth` decimal(10,2) DEFAULT NULL,
  `gross_margin` decimal(10,2) DEFAULT NULL,
  `operating_margin` decimal(10,2) DEFAULT NULL,
  `dividend_yield` decimal(10,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_stock_date` (`stock_code`,`date`) USING BTREE,
  KEY `idx_fundamental_date` (`date`) USING BTREE,
  CONSTRAINT `fundamental_metrics_ibfk_1` FOREIGN KEY (`stock_code`) REFERENCES `stocks` (`stock_code`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=243192 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for industry_metrics
-- ----------------------------
DROP TABLE IF EXISTS `industry_metrics`;
CREATE TABLE `industry_metrics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `date` date DEFAULT NULL,
  `profit_margin` decimal(10,2) DEFAULT NULL,
  `price_to_sales` decimal(10,2) DEFAULT NULL,
  `industry_rank` int DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_stock_date` (`stock_code`,`date`) USING BTREE,
  KEY `idx_industry_date` (`date`) USING BTREE,
  CONSTRAINT `industry_metrics_ibfk_1` FOREIGN KEY (`stock_code`) REFERENCES `stocks` (`stock_code`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=241327 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for investor_metrics
-- ----------------------------
DROP TABLE IF EXISTS `investor_metrics`;
CREATE TABLE `investor_metrics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `date` date DEFAULT NULL,
  `insider_holding` decimal(10,2) DEFAULT NULL,
  `institution_holding` decimal(10,2) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_stock_date` (`stock_code`,`date`) USING BTREE,
  KEY `idx_investor_date` (`date`) USING BTREE,
  CONSTRAINT `investor_metrics_ibfk_1` FOREIGN KEY (`stock_code`) REFERENCES `stocks` (`stock_code`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=240893 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for stock_chip_analysis
-- ----------------------------
DROP TABLE IF EXISTS `stock_chip_analysis`;
CREATE TABLE `stock_chip_analysis` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `stock_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `industry` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `analysis_date` date NOT NULL,
  `strategy_type` enum('低吸','追涨','潜力') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `close_price` decimal(10,2) NOT NULL,
  `ma60` decimal(10,2) DEFAULT NULL,
  `vwap` decimal(10,2) DEFAULT NULL,
  `profit_chip_ratio` decimal(10,4) DEFAULT NULL,
  `locked_chip_ratio` decimal(10,4) DEFAULT NULL,
  `main_chip_ratio` decimal(10,4) DEFAULT NULL,
  `floating_chip_ratio` decimal(10,4) DEFAULT NULL,
  `rank_num` int NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_stock_date_type` (`stock_code`,`analysis_date`,`strategy_type`) USING BTREE,
  KEY `idx_analysis_date` (`analysis_date`) USING BTREE,
  KEY `idx_strategy_rank` (`strategy_type`,`rank_num`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=1991 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for stock_historical_quotes
-- ----------------------------
DROP TABLE IF EXISTS `stock_historical_quotes`;
CREATE TABLE `stock_historical_quotes` (
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
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
  `source` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '数据来源(yfinance/akshare)',
  `adjust_type` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '复权类型(qfq/hfq/none)',
  PRIMARY KEY (`stock_code`,`trade_date`) USING BTREE,
  KEY `idx_stock_code` (`stock_code`) USING BTREE,
  KEY `idx_stock_change` (`stock_code`,`change_ratio`) USING BTREE,
  CONSTRAINT `stock_historical_quotes_ibfk_1` FOREIGN KEY (`stock_code`) REFERENCES `stocks` (`stock_code`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票历史交易数据';

-- ----------------------------
-- Table structure for stock_recommendations
-- ----------------------------
DROP TABLE IF EXISTS `stock_recommendations`;
CREATE TABLE `stock_recommendations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `recommend_date` date NOT NULL COMMENT '推荐日期',
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
  `stock_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票名称',
  `industry` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '所属行业',
  `current_price` decimal(10,2) DEFAULT NULL COMMENT '当前价格',
  `total_score` int DEFAULT NULL COMMENT '综合评分',
  `recommendation_level` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '推荐等级',
  `reasons` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci COMMENT '推荐理由',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_date_stock` (`recommend_date`,`stock_code`) USING BTREE,
  KEY `idx_date` (`recommend_date`) USING BTREE,
  KEY `idx_score` (`total_score`) USING BTREE,
  KEY `idx_stock` (`stock_code`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=201 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票推荐记录表';

-- ----------------------------
-- Table structure for stock_technical_scores
-- ----------------------------
DROP TABLE IF EXISTS `stock_technical_scores`;
CREATE TABLE `stock_technical_scores` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '股票代码',
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
  `rsi` decimal(10,2) DEFAULT NULL COMMENT 'RSI指标',
  `kdj_k` decimal(10,2) DEFAULT NULL COMMENT 'KDJ_K值',
  `kdj_d` decimal(10,2) DEFAULT NULL COMMENT 'KDJ_D值',
  `macd` decimal(10,2) DEFAULT NULL COMMENT 'MACD值',
  `macd_signal` decimal(10,2) DEFAULT NULL COMMENT 'MACD信号线',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `vol_ma5` decimal(20,2) DEFAULT NULL COMMENT '5日均量',
  `vol_ma20` decimal(20,2) DEFAULT NULL COMMENT '20日均量',
  `volatility` decimal(10,4) DEFAULT NULL COMMENT '波动率',
  `boll_upper` decimal(10,2) DEFAULT NULL COMMENT '布林带上轨',
  `boll_lower` decimal(10,2) DEFAULT NULL COMMENT '布林带下轨',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_stock_date` (`stock_code`,`score_date`) USING BTREE,
  KEY `idx_date_score` (`score_date`,`total_score`) USING BTREE,
  KEY `idx_stock_date` (`stock_code`,`score_date`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2068 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票技术评分表';

-- ----------------------------
-- Table structure for stocks
-- ----------------------------
DROP TABLE IF EXISTS `stocks`;
CREATE TABLE `stocks` (
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `stock_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `sector` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `industry` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `company_name_en` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `address` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `website` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `employees` int DEFAULT NULL,
  `listing_date` date DEFAULT NULL,
  `update_time` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`stock_code`) USING BTREE,
  KEY `idx_stock_sector` (`sector`) USING BTREE,
  KEY `idx_stock_industry` (`industry`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for technical_metrics
-- ----------------------------
DROP TABLE IF EXISTS `technical_metrics`;
CREATE TABLE `technical_metrics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `stock_code` varchar(6) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `date` date DEFAULT NULL,
  `current_price` decimal(10,2) DEFAULT NULL,
  `high_52week` decimal(10,2) DEFAULT NULL,
  `low_52week` decimal(10,2) DEFAULT NULL,
  `volume` bigint DEFAULT NULL,
  `avg_volume` bigint DEFAULT NULL,
  `avg_volume_10d` bigint DEFAULT NULL,
  `ma_200` decimal(10,2) DEFAULT NULL,
  `beta` decimal(10,4) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_stock_date` (`stock_code`,`date`) USING BTREE,
  KEY `idx_technical_date` (`date`) USING BTREE,
  CONSTRAINT `technical_metrics_ibfk_1` FOREIGN KEY (`stock_code`) REFERENCES `stocks` (`stock_code`) ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB AUTO_INCREMENT=248603 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ----------------------------
-- Table structure for update_logs
-- ----------------------------
DROP TABLE IF EXISTS `update_logs`;
CREATE TABLE `update_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `table_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `update_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `start_time` timestamp NULL DEFAULT NULL,
  `end_time` timestamp NULL DEFAULT NULL,
  `status` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `records_affected` int DEFAULT NULL,
  `error_message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_update_logs_table` (`table_name`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET FOREIGN_KEY_CHECKS = 1;
