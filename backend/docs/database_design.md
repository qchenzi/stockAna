# 股票数据分析系统 - 数据库设计文档

## 1. 概述

### 1.1 设计目标
- 存储和管理 A 股上市公司的各类指标数据
- 支持历史数据追踪和时间序列分析
- 确保数据的完整性和一致性
- 便于数据更新和维护

### 1.2 数据来源
- Yahoo Finance API
- 东方财富网数据
- 其他金融数据源

## 2. 数据库结构

### 2.1 股票基本信息表 (stocks)
存储股票的基本信息，相对稳定的数据。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| stock_code | VARCHAR(6) | 股票代码 | PRIMARY KEY |
| stock_name | VARCHAR(50) | 股票名称 | NOT NULL |
| sector | VARCHAR(50) | 所属板块 | |
| industry | VARCHAR(100) | 所属行业 | |
| company_name_en | VARCHAR(200) | 公司英文名 | |
| description | TEXT | 公司描述 | |
| address | VARCHAR(200) | 公司地址 | |
| website | VARCHAR(100) | 公司网站 | |
| employees | INT | 员工人数 | |
| listing_date | DATE | 上市日期 | |
| update_time | TIMESTAMP | 数据更新时间 | |

### 2.2 基本面指标表 (fundamental_metrics)
存储每日更新的基本面指标���据。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 自增ID | PRIMARY KEY |
| stock_code | VARCHAR(6) | 股票代码 | FOREIGN KEY |
| date | DATE | 数据日期 | |
| pe_ratio | DECIMAL(10,2) | 市盈率 | |
| pb_ratio | DECIMAL(10,2) | 市净率 | |
| roe | DECIMAL(10,2) | 净资产收益率 | |
| revenue_growth | DECIMAL(10,2) | 收入增长率 | |
| earnings_growth | DECIMAL(10,2) | 盈利增长率 | |
| gross_margin | DECIMAL(10,2) | 毛利率 | |
| operating_margin | DECIMAL(10,2) | 营业利润率 | |

### 2.3 技术面指标表 (technical_metrics)
存储实时或每日更新的技术面指标。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 自增ID | PRIMARY KEY |
| stock_code | VARCHAR(6) | 股票代码 | FOREIGN KEY |
| date | DATE | 数据日期 | |
| current_price | DECIMAL(10,2) | 当前股价 | |
| high_52week | DECIMAL(10,2) | 52周最高 | |
| low_52week | DECIMAL(10,2) | 52周最低 | |
| volume | BIGINT | 成交量 | |
| avg_volume | BIGINT | 日均成交量 | |
| avg_volume_10d | BIGINT | 10日均量 | |
| ma_200 | DECIMAL(10,2) | 200日均价 | |
| update_time | TIMESTAMP | 更新时间 | |

### 2.4 财务健康指标表 (financial_health)
存储季度更新的财务健康指标。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 自增ID | PRIMARY KEY |
| stock_code | VARCHAR(6) | 股票代码 | FOREIGN KEY |
| report_date | DATE | 报告期 | |
| quick_ratio | DECIMAL(10,2) | 速动比率 | |
| current_ratio | DECIMAL(10,2) | 流动比率 | |
| debt_to_equity | DECIMAL(10,2) | 资产负债率 | |
| operating_cashflow | DECIMAL(15,2) | 经营现金流 | |
| free_cashflow | DECIMAL(15,2) | 自由现金流 | |

### 2.5 行业指标表 (industry_metrics)
存储行业相关指标数据。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 自增ID | PRIMARY KEY |
| stock_code | VARCHAR(6) | 股票代码 | FOREIGN KEY |
| date | DATE | 数据日期 | |
| profit_margin | DECIMAL(10,2) | 行业利润率 | |
| price_to_sales | DECIMAL(10,2) | 市销率 | |
| industry_rank | INT | 行业排名 | |

### 2.6 投资者行为表 (investor_metrics)
存储投资者持股等信息。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 自增ID | PRIMARY KEY |
| stock_code | VARCHAR(6) | 股票代码 | FOREIGN KEY |
| date | DATE | 数据日期 | |
| insider_holding | DECIMAL(10,2) | 内部持股比例 | |
| institution_holding | DECIMAL(10,2) | 机构持股比例 | |

### 2.7 公司高管信息表 (company_officers)
存储公司高管信息。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 自增ID | PRIMARY KEY |
| stock_code | VARCHAR(6) | 股票代码 | FOREIGN KEY |
| name | VARCHAR(100) | 高管姓名 | |
| title | VARCHAR(100) | 职位 | |
| age | INT | 年龄 | |
| since_date | DATE | 任职日期 | |

### 2.8 数据更新日志表 (update_logs)
记录数据更新情况。

| 字段名 | 类型 | 说明 | 约束 |
|--------|------|------|------|
| id | BIGSERIAL | 自增ID | PRIMARY KEY |
| table_name | VARCHAR(50) | 更新的表名 | |
| update_type | VARCHAR(20) | 更新类型 | |
| start_time | TIMESTAMP | 开始时间 | |
| end_time | TIMESTAMP | 结束时间 | |
| status | VARCHAR(20) | 更新状态 | |
| records_affected | INT | 影响的记录数 | |
| error_message | TEXT | 错误信息 | |

## 3. 索引设计

### 3.1 主键索引
- 每个表都有自己的主键索引（id 或 stock_code）

### 3.2 外键索引
- 所有关联到 stocks 表的 stock_code 字段

### 3.3 复合索引
- (stock_code, date) 用于快速查询特定股票的历史数据
- (date, sector) 用于板块分析

## 4. 数据维护

### 4.1 数据更新策略
- 基本信息：按需更新
- 交易数据：每日更新
- 财务数据：季度更新
- 其他指标：根据数据源更新��率决定

### 4.2 数据备份策略
- 每日增量备份
- 每周全量备份
- 保留最近一个月的备份

## 5. 性能优化

### 5.1 分区策略
- 按时间分区：大型表按年份分区
- 按板块分区：可选择性地对大表进行板块分区

### 5.2 查询优化
- 使用适当的索引
- 优化常用查询
- 使用物化视图存储常用统计数据

## 6. 安全性设计

### 6.1 访问控制
- 只读用户：用于查询
- 写入用户：用于数据更新
- 管理用户：用于维护

### 6.2 数据审计
- 记录重要数据的修改历史
- 监控异常访问 