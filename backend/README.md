# 上证股票数据采集与分析系统

这是一个用于采集和分析上证股票数据的系统。系统分为数据采集、数据分析、数据入库和策略评分四个模块。

## 系统组件

1. `sh_stock_scraper.py`: 爬取上证股票列表
2. `sh_stock_downloader.py`: 下载股票详细信息
3. `sh_stock_analyzer.py`: 分析和整理股票指标数据
4. `sh_stock_db.py`: 数据库操作模块
5. `sh_stock_scorer.py`: 股票评分策略模块
6. `scripts/create_tables.sql`: 数据库表结构
7. `scripts/clean_data.sql`: 数据清理脚本

## 使用方法

### 1. 初始化数据库
```bash
# 创建数据库和表结构
mysql -u your_username -p < scripts/create_tables.sql
```

### 2. 数据采集
```bash
# 第一步：获取上证股票列表
python3 sh_stock_scraper.py

# 第二步：下载股票详细信息（支持并发）
python3 sh_stock_downloader.py --workers 10
```

### 3. 数据分析
```bash
# 默认模式：只处理最新日期的数据
python3 sh_stock_analyzer.py

# 处理所有历史数据
python3 sh_stock_analyzer.py --full
```

### 4. 数据入库
```bash
# 处理最新一天数据
python3 sh_stock_db.py

# 处理所有历史数据，并设置20个并发
python3 sh_stock_db.py --full --workers 20

# 处理指定日期的数据
python3 sh_stock_db.py --date 2024-03-20

# 清理数据库中的历史数据
python3 scripts/clean_data.py --date 2024-12-20
python3 scripts/clean_data.py --all
```

### 5. 策略评分
```bash
# 使用RTPV策略（默认，且计算周期为30天）
python3 sh_stock_scorer.py --top 20

# 使用价值型策略
python3 sh_stock_scorer.py --strategy value --top 20

# 使用其他策略
python3 sh_stock_scorer.py --strategy growth --top 20
python3 sh_stock_scorer.py --strategy income --top 20
python3 sh_stock_scorer.py --strategy trend --top 20
python3 sh_stock_scorer.py --strategy reverse --top 20

# 指定评分日期和周期（周期只有RTPV使用
python3 sh_stock_scorer.py --date 2024-03-20 --period 14

# 显示前20名股票
python3 sh_stock_scorer.py --top 20

# 完整参数示例
python3 sh_stock_scorer.py --strategy rtpv --date 2024-03-20 --period 14 --top 20
```

## 评分策略说明

### 1. RTPV综合评分策略 (权重配比: 30-30-30-10)
- **净资产收益率(ROE)** - 权重30%
  * 反映公司利用股东投入资本创造利润的能力
  * 计算公式：净利润/净资产
  * 评分标准：净资产收益率越高得分越高
  
- **相对强弱指标(RSI)** - 权重30%
  * 技术面指标，衡量股价超买超卖情况
  * RSI > 70: 超买区间，股价可能高估
  * RSI < 30: 超卖区间，股价可能低估
  
- **价格变动幅度** - 权重30%
  * 计算周期内的股价变动百分比
  * 评分标准：上涨幅度越大得分越高
  
- **成交量比值** - 权重10%
  * 当日成交量与过去平均成交量的比值
  * 评分标准：成交量放大得分越高

### 2. 价值型投资策略
- **市盈率(PE)** (30分)
  * 股价与每股收益的比值
  * 低于行业平均市盈率20%以上得30分
  * 反映股票的估值水平

- **市净率(PB)** (20分)
  * 股价与每股净资产的比值
  * 低于3倍得20分
  * 反映公司的账面价值

- **净资产收益率(ROE)** (30分)
  * 反映公司盈利能力
  * 高于15%得30分
  * 衡量资本使用效率

- **毛利率** (10分)
  * (营业收入-营业成本)/营业收入
  * 高于40%得10分
  * 反映产品的盈利能力

- **行业排名** (10分)
  * 公司在行业中的综合排名
  * 行业前5名得10分

### 3. 成长型投资策略
- **营业收入增长率** (30分)
  * 年度营收增长超过20%得30分
  * 反映公司业务规模扩张速度

- **净利润增长率** (30分)
  * 年度利润增长超过25%得30分
  * 反映公司盈利能力上升情况

- **价格趋势** (20分)
  * 当前股价高于200日均线得20分
  * 反映中长期上涨趋势

- **流动比率** (20分)
  * 流动资产/流动负债
  * 大于等于1.5得20分
  * 反映短期偿债能力

### 4. 收益型投资策略
- **股息率** (40分)
  * 年度现金分红/股价
  * 高于5%得40分
  * 反映投资回报率

- **贝塔系数** (30分)
  * 股价波动与大盘相关性
  * 低于0.6得30分
  * 反映抗跌能力

- **速动比率** (30分)
  * (流动资产-存货)/流动负债
  * 高于1.5得30分
  * 反映即时偿债能力

### 5. 趋势交易策略
- **股价位置** (30分)
  * 当前价格接近52周最高点得高分
  * 反映上涨动能

- **成交量** (30分)
  * 股价上涨时成交量放大得高分
  * 反映买盘力量

- **相对强弱指标** (40分)
  * RSI在50-80区间得高分
  * 反映上涨趋势强度

### 6. 反向投资策略
- **股价位置** (40分)
  * 当前价格接近52周最低点得高分
  * 寻找超跌反弹机会

- **净资产收益率** (30分)
  * 基本面良好的公司得高分
  * 确保公司经营稳健

- **毛利率** (20分)
  * 产品盈利能力强的公司得高分
  * 具备竞争优势

- **内部持股** (10分)
  * 高管持股比例高得高分
  * 反映管理层���心

## 数据处理流程

1. **数据采集**:
   - 获取上证股票列表
   - 下载每只股票的详细信息
   - 按日期和行业分类保存原始数据

2. **数据分析**:
   - 处理和整理各类指标数据：
     * 基本面指标 (fundamental)
     * 技术面指标 (technical)
     * 财务健康指标 (financial)
     * 行业指标 (industry)
     * 投资者行为指标 (investor)
   - 生成行业分析报告
   - 保存处理后的指标数据

3. **数据入库**:
   - 将处理后的数据保存到数据库
   - 支持增量更新和并发处理
   - 记录数据更新日志

4. **策略评分**:
   - 支持多种评分策略
   - 可配置计算周期
   - 输出详细的评分报告

## 目录结构
```
project/
├── stock_info/               # 原始数据目录
│   └── YYYY-MM-DD/          # 按日期组织的数据
│       └── Technology/      # 行业分类
│           └── 股票数据.json
├── stock_analysis/          # 分析结果目录
│   └── YYYY-MM-DD/         # 按日期组织的分析结果
│       └── Technology/     # 行业分类
│           ├── fundamental/ # 基本面指标
│           ├── technical/   # 技术面指标
│           ├── financial/   # 财务健康指标
│           ├── industry/    # 行业指标
│           ├── investor/    # 投资者行为指标
│           ├── summary.csv  # 汇总数据
│           └── stats.txt    # 统计报告
└── scripts/                # 脚本目录
    ├── create_tables.sql  # 建表脚本
    └── clean_data.sql    # 数据清理脚本
```

## 注意事项

1. 确保已安装所需的Python包：
```bash
pip3 install yfinance pandas sqlalchemy pymysql tqdm
```

2. 配置数据库连接信息：
   - 在 `config/database.py` 中设置数据库连接参数

3. 建议每天固定时间运行数据采集和分析程序
4. 数据清理谨慎使用，建议先备份数据
5. 评分策略的参数可根据实际需求调整

## 常见问题

1. **数据采集失败**：
   - 检查网络连接
   - 确认股票代码格式正确
   - 可能需要等待一段时间后重试

2. **数据分析错误**：
   - 检查原始数据完整性
   - 查看错误日志进行排查
   - 确保目录结构正确

3. **数据库操作问题**：
   - 检查数据库连接配置
   - 确认数据库表结构完整
   - 查看错误日志进行排查

4. **评分策略问题**：
   - 确保数据库中有足够的历史数据
   - 检查计算周期是否合适
   - 可以调整指标权重

## HTTP API 接口

服务支��通过 HTTP API 访问所有功能，所有接口都返回 JSON 格式数据。

### 基础信息

- 基础URL: `http://your-server:5000`
- 返回格式: JSON
- 编码方式: UTF-8

### API 列表

#### 1. 测试服务状态

```bash
GET /test

# 示例
curl http://localhost:5000/test

# 返回
{
    "status": "ok",
    "message": "Service is running",
    "timestamp": "2024-12-25 22:45:30"
}
```

#### 2. 获取策略列表

```bash
GET /api/strategies

# 示例
curl http://localhost:5000/api/strategies

# 返回
{
    "strategies": {
        "rtpv": "RTPV综合策略",
        "value": "价值投资策略",
        "growth": "成长投资策略",
        "income": "收益投资策略",
        "trend": "趋势交易策略",
        "reverse": "反向投资策略"
    }
}
```

#### 3. 获取策略评分结果

```bash
GET /api/stocks/<strategy>

参数：
- strategy: 策略名称（必填）
- top: 返回前N名股票（可选，默认20）
- date: 评分日期（可选，YYYY-MM-DD）
- period: 计算周期（可选，仅RTPV策略支持）

# 示例：获取 RTPV 策略前10名
curl "http://localhost:5000/api/stocks/rtpv?top=10"

# 示例：获取指定日期的价值策略
curl "http://localhost:5000/api/stocks/value?date=2024-12-25&top=20"

# 返���
{
    "strategy": "value",
    "date": "2024-12-25",
    "summary": "计算 2024-12-25 的价值型投资策略",
    "indicators": [
        "pe_ratio: 市盈率，反映股票估值水平",
        "pb_ratio: 市净率，反映公司账面价值",
        "roe: 净资产收益率，反映公司盈利能力"
    ],
    "scoring_rules": [
        "1. 市盈率(30分): 低于行业均值20%得30分",
        "2. 市净率(20分): <3倍得20分，<5倍得10分",
        "3. ROE(30分): >15%得30分，>10%得20分"
    ],
    "stocks": [
        {
            "code": "600519",
            "name": "贵州茅台",
            "score": 95.0,
            "metrics": {
                "industry": "白酒",
                "pe_ratio": 18.5,
                "pb_ratio": 8.2,
                "roe": 35.8,
                "gross_margin": 91.2,
                "industry_rank": 1
            }
        }
    ]
}
```

#### 4. 条件筛选股票

```bash
GET /api/stocks/filter

参数：
- pe_min: 最小市盈率
- pe_max: 最大市盈率
- pb_min: 最小市净率
- pb_max: 最大市净率
- roe_min: 最小ROE
- dividend_min: 最小股息率
- industry: 行业名称

# 示例：筛选低估值高收益股票
curl "http://localhost:5000/api/stocks/filter?pe_max=30&roe_min=15"

# 示例：筛选高股息科技股
curl "http://localhost:5000/api/stocks/filter?industry=科技&dividend_min=5"

# 返回
{
    "stocks": [
        {
            "code": "600519",
            "name": "贵州茅台",
            "industry": "白酒",
            "price": 1800.0,
            "pe": 18.5,
            "pb": 8.2,
            "roe": 35.8,
            "dividend": 1.5,
            "volume": 1234567
        }
    ]
}
```

#### 5. 获取个股详细信息

```bash
GET /api/stocks/<code>

# 示例：查询贵州茅台
curl http://localhost:5000/api/stocks/600519

# 返回
{
    "stock": {
        "stock_code": "600519",
        "stock_name": "贵州茅台",
        "industry": "白酒",
        "current_price": 1800.0,
        "pe_ratio": 18.5,
        "pb_ratio": 8.2,
        "roe": 35.8,
        "dividend_yield": 1.5,
        "gross_margin": 91.2,
        "volume": 1234567,
        "ma_5": 1790.0,
        "ma_10": 1785.0,
        "ma_20": 1780.0,
        "ma_60": 1770.0
    }
}
```

### 错误处理

所有接口在发生错误时都会返回统一格式的错误信息：

```json
{
    "error": "错误描述信息"
}
```

常见 HTTP 状态码：
- 200: 请求成功
- 400: 请求参数错误
- 404: 资源不存在
- 500: 服务器内部错误

### 使用建议

1. 建议使用 Python requests 库进行接口调用：
```python
import requests

# 获取策略列表
response = requests.get('http://localhost:5000/api/strategies')
strategies = response.json()

# 获取策略评分
response = requests.get('http://localhost:5000/api/stocks/rtpv', 
                       params={'top': 10})
scores = response.json()

# 条件筛选
response = requests.get('http://localhost:5000/api/stocks/filter', 
                       params={'pe_max': 30, 'roe_min': 15})
stocks = response.json()
```

2. 使用 curl 进行测试：
```bash
# 使用 jq 格式化输出
curl "http://localhost:5000/api/stocks/rtpv?top=10" | jq

# 使用 Python 格式化输出
curl "http://localhost:5000/api/stocks/rtpv?top=10" | python3 -m json.tool
```

## 内网穿透配置（使用 frp）

本项目使用 frp 实现内网穿透，使外网可以访问服务。配置步骤如下：

### 1. 服务端配置（在有公网IP的服务器上）

```bash
# 1. 下载 frp
wget https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_linux_amd64.tar.gz
tar xf frp_0.51.3_linux_amd64.tar.gz
cd frp_0.51.3_linux_amd64

# 2. 创建服务端配置文件 frps.ini
cat > frps.ini << EOF
[common]
bind_port = 7000
token = your_token_here  # 设置一个��全的token
EOF

# 3. 启动服务端
./frps -c frps.ini

# 4. 检查服务是否正常运行
netstat -tlnp | grep 7000
```

### 2. 客户端配置（在本地机器上）

```bash
# 1. 下载 frp
wget https://github.com/fatedier/frp/releases/download/v0.51.3/frp_0.51.3_linux_amd64.tar.gz
tar xf frp_0.51.3_linux_amd64.tar.gz
cd frp_0.51.3_linux_amd64

# 2. 创建客户端配置文件 frpc.ini
cat > frpc.ini << EOF
[common]
server_addr = your_server_ip  # 你的服务器IP
server_port = 7000
token = your_token_here      # 与服务端相同的token

[web]
type = tcp
local_ip = 127.0.0.1
local_port = 5000
remote_port = 8000          # 外网访问端口
EOF

# 3. 启动客户端
./frpc -c frpc.ini
```

### 3. 防火墙配置

```bash
# 在服务器上配置防火墙
sudo firewall-cmd --zone=public --add-port=7000/tcp --permanent  # frp服务端口
sudo firewall-cmd --zone=public --add-port=8000/tcp --permanent  # 外网访问端口
sudo firewall-cmd --reload

# 检查端口是否开放
sudo firewall-cmd --list-ports
```

### 4. 测试连接

```bash
# 1. 确保 Flask 服务正在运行
python3 wx_stock_server.py &

# 2. 测试本地访问
curl http://localhost:5000/test

# 3. 测试外网访问
curl http://your_server_ip:8000/test
```

### 5. 设置开机自启

1. 创建服务启动脚本 `start_service.sh`：
```bash
#!/bin/bash

# 启动 Flask 服务
cd /path/to/your/project
python3 wx_stock_server.py &

# 等待服务启动
sleep 2

# 启动 frp 客户端
cd /path/to/frp
./frpc -c frpc.ini
```

2. 添加执行权限：
```bash
chmod +x start_service.sh
```

3. 配置 Supervisor：
```bash
sudo vim /etc/supervisor/conf.d/stock_service.conf

[program:stock_service]
command=/path/to/start_service.sh
directory=/path/to/project
user=root
autostart=true
autorestart=true
stderr_logfile=/var/log/stock_service.err.log
stdout_logfile=/var/log/stock_service.out.log
```

4. 启动服务：
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start stock_service
```

### 6. 常见问题排查

1. 连接失败：
```bash
# 检查服务端状态
ps aux | grep frps
netstat -tlnp | grep 7000

# 检查客户端状态
ps aux | grep frpc
netstat -tlnp | grep 5000
```

2. 端口问题：
```bash
# 检查防火墙
sudo firewall-cmd --list-all

# 检查端口占用
netstat -tlnp | grep 8000
```

3. 查看日志：
```bash
# 服务端日志
tail -f /var/log/frps.log

# 客户端日志
tail -f /var/log/frpc.log

# Supervisor 日志
tail -f /var/log/stock_service.err.log
```

### 7. 安全建议

1. 使用强密码的 token
2. 定期更新 frp 版本
3. 配置服务器防火墙
4. 使用 HTTPS 进行���密传输
5. 定期检查日志文件

## 在线演示

系统已部署并提供以下公开 API 接口：

### 基础 URL
```
http://tech-chen.pics:8000
```

### 示例接口

1. 获取策略列表：
```
http://tech-chen.pics:8000/api/strategies
```

2. RTPV 综合策略（前10名）：
```
# 基本用法
http://tech-chen.pics:8000/api/stocks/rtpv?top=10

# 指定周期
http://tech-chen.pics:8000/api/stocks/rtpv?top=10&period=14

# 指定日期
http://tech-chen.pics:8000/api/stocks/rtpv?top=10&date=2024-12-25
```

3. 价值投资策略：
```
# 基本用法
http://tech-chen.pics:8000/api/stocks/value?top=20

# 指定日期
http://tech-chen.pics:8000/api/stocks/value?top=20&date=2024-12-25
```

4. 成长投资策略：
```
# 基本用法
http://tech-chen.pics:8000/api/stocks/growth?top=20

# 指定日期
http://tech-chen.pics:8000/api/stocks/growth?top=20&date=2024-12-25
```

5. 收益投资策略：
```
# 基本用法
http://tech-chen.pics:8000/api/stocks/income?top=20

# 指定日期
http://tech-chen.pics:8000/api/stocks/income?top=20&date=2024-12-25
```

6. 趋势交易策略：
```
# 基本用法
http://tech-chen.pics:8000/api/stocks/trend?top=20

# 指定日期
http://tech-chen.pics:8000/api/stocks/trend?top=20&date=2024-12-25
```

7. 反向投资策略：
```
# 基本用法
http://tech-chen.pics:8000/api/stocks/reverse?top=20

# 指定日期
http://tech-chen.pics:8000/api/stocks/reverse?top=20&date=2024-12-25
```

8. 条件筛选（支持多个条件组合）：
```
# 低估值高收益
http://tech-chen.pics:8000/api/stocks/filter?pe_max=30&roe_min=15

# 高股息科技股
http://tech-chen.pics:8000/api/stocks/filter?industry=科技&dividend_min=5

# 低估值高成长
http://tech-chen.pics:8000/api/stocks/filter?pe_max=20&roe_min=20&pb_max=3
```

9. 个股详细信息：
```
# 查询贵州茅台
http://tech-chen.pics:8000/api/stocks/600519

# 查询腾讯控股
http://tech-chen.pics:8000/api/stocks/00700
```

10. 技术分析接口：
```
# 获取均线数据（MA5/MA10/MA200）
http://tech-chen.pics:8000/api/technical/ma/600519?date=2024-03-20

# 获取均线交叉信号（金叉/死叉）
http://tech-chen.pics:8000/api/technical/cross/600519?date=2024-03-20

# 获取三连阳形态
http://tech-chen.pics:8000/api/technical/three-bullish/600519?date=2024-03-20

# 获取吞没形态（看涨/看跌吞没）
http://tech-chen.pics:8000/api/technical/engulfing/600519?date=2024-03-20

# 获取支撑位和阻力位
http://tech-chen.pics:8000/api/technical/support-resistance/600519?date=2024-03-20
```

### Python 调用示例

```python
import requests

# 基础 URL
base_url = 'http://tech-chen.pics:8000'

# 1. 获取策略列表
response = requests.get(f'{base_url}/api/strategies')
print("策略列表:", response.json())

# 2. RTPV 策略评分
response = requests.get(f'{base_url}/api/stocks/rtpv', 
                       params={'top': 10, 'period': 14})
print("RTPV策略:", response.json())

# 3. 价值策略评分
response = requests.get(f'{base_url}/api/stocks/value', 
                       params={'top': 20})
print("价值策略:", response.json())

# 4. 成长策略评分
response = requests.get(f'{base_url}/api/stocks/growth', 
                       params={'top': 20})
print("成长策略:", response.json())

# 5. 条件筛选
response = requests.get(f'{base_url}/api/stocks/filter', 
                       params={
                           'pe_max': 30,
                           'roe_min': 15,
                           'dividend_min': 3
                       })
print("条件筛选:", response.json())

# 6. 个股信息
response = requests.get(f'{base_url}/api/stocks/600519')
print("个股信息:", response.json())

# 7. 技术分析示例
# 获取均线数据
response = requests.get(f'{base_url}/api/technical/ma/600519', 
                       params={'date': '2024-03-20'})
print("均线数据:", response.json())

# 获取均线交叉信号
response = requests.get(f'{base_url}/api/technical/cross/600519', 
                       params={'date': '2024-03-20'})
print("交叉信号:", response.json())

# 获取支撑位和阻力位
response = requests.get(f'{base_url}/api/technical/support-resistance/600519', 
                       params={'date': '2024-03-20'})
print("支撑阻力位:", response.json())
```

### curl 测试示例

```bash
# 1. 获取策略列表
curl "http://tech-chen.pics:8000/api/strategies" | jq

# 2. RTPV策略（带周期参数）
curl "http://tech-chen.pics:8000/api/stocks/rtpv?top=10&period=14" | jq

# 3. 价值策略（指定日期）
curl "http://tech-chen.pics:8000/api/stocks/value?top=20&date=2024-12-25" | jq

# 4. 成长策略
curl "http://tech-chen.pics:8000/api/stocks/growth?top=20" | jq

# 5. 条件筛选
curl "http://tech-chen.pics:8000/api/stocks/filter?pe_max=30&roe_min=15" | jq

# 6. 个股信息
curl "http://tech-chen.pics:8000/api/stocks/600519" | jq

# 7. 技术分析接口
# 获取均线数据
curl "http://tech-chen.site/api/technical/ma/600519?date=2025-01-10" | jq

# 获取均线交叉信号
curl "http://tech-chen.site/api/technical/cross/600519?date=2025-01-10" | jq

# 获取三连阳形态
curl "http://tech-chen.site/api/technical/three-bullish/600519?date=2025-01-10" | jq

# 获取吞没形态
curl "http://tech-chen.site/api/technical/engulfing/600519?date=2025-01-10" | jq

# 获取支撑位和阻力位
curl "http://tech-chen.site/api/technical/support-resistance/600519?date=2025-01-10" | jq
```

### 技术分析接口说明

1. 均线数据 (/api/technical/ma/<stock_code>)
- 返回 MA5、MA10、MA200 等均线数据
- 用于判断股价趋势和支撑阻力位

2. 均线交叉 (/api/technical/cross/<stock_code>)
- 返回 MA5 和 MA20 的交叉信号
- 金叉：短期均线上穿长期均线，可能预示上涨
- 死叉：短期均线下穿长期均线，可能预示下跌

3. 三连阳形态 (/api/technical/three-bullish/<stock_code>)
- 检测连续三天上涨的形态
- 可能预示强势上涨趋势的形成

4. 吞没形态 (/api/technical/engulfing/<stock_code>)
- 检测看涨或看跌吞没形态
- 用于判断可能的趋势反转点

5. 支撑阻力位 (/api/technical/support-resistance/<stock_code>)
- 返回基于历史数据计算的支撑位和阻力位
- 包含20日内的最高价和最低价
- 同时返回20日平均成交量

### 使用说明

1. 所有接口都返回 JSON 格式数据
2. 支持跨域访问
3. 无需认证即可访问
4. 建议使用 HTTPS 进行安全访问

### 在线测试工具

可以使用以下工具测试 API：

1. 使用 curl：
```bash
curl "http://tech-chen.pics:8000/api/stocks/rtpv?top=10"
```

2. 使用 Python：
```python
import requests

response = requests.get('http://tech-chen.pics:8000/api/stocks/rtpv', 
                       params={'top': 10})
print(response.json())
```

3. 使用浏览器直接访问：
- 打开浏览器
- 输入 URL：`http://tech-chen.pics:8000/api/strategies`
- 使用浏览器插件（如 JSONView）格式化显示