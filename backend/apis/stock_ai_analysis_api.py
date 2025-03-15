from flask import Blueprint, request, jsonify
from sqlalchemy import text, create_engine
from config.config import AI_API_KEY, AI_API_URL
from config.database import DB_CONFIG_READER
import logging
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# 创建蓝图
ai_analysis_bp = Blueprint('ai_analysis', __name__)

# 配置日志
logger = logging.getLogger(__name__)

# 创建数据库连接
engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG_READER['user']}:{DB_CONFIG_READER['password']}"
    f"@{DB_CONFIG_READER['host']}/{DB_CONFIG_READER['database']}?charset=utf8mb4"
)

class AIAnalyzer:
    def __init__(self):
        self.api_key = AI_API_KEY
        self.url = AI_API_URL
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        # 创建一个不使用代理的 session
        self.session = requests.Session()
        self.session.trust_env = False  # 不使用系统环境变量中的代理设置

    @retry(
        stop=stop_after_attempt(3),  # 最多重试3次
        wait=wait_exponential(multiplier=2, min=4, max=60),  # 指数退避，等待时间更长
        reraise=True
    )
    def get_analysis(self, messages):
        """带重试机制的AI分析调用"""
        try:
            data = {
                "model": "deepseek-chat",
                "messages": messages,
                "stream": False
            }
            
            # 使用更长的超时时间
            response = self.session.post(
                self.url, 
                headers=self.headers, 
                json=data,
                timeout=(30, 120)  # (连接超时, 读取超时)
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                logger.error(f"API调用失败: {response.status_code} - {response.text}")
                raise Exception(f"API调用失败: {response.status_code}")
                
        except requests.Timeout as e:
            logger.error(f"请求超时: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"AI分析调用失败: {str(e)}")
            raise

def get_technical_analysis(stock_code, date):
    """获取技术分析结果"""
    try:
        with engine.connect() as conn:
            # 先检查是否有数据
            date_check = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM stock_historical_quotes
                WHERE stock_code = :code 
                AND trade_date = :date
            """), {'code': stock_code, 'date': date}).fetchone()

            if not date_check or date_check.count == 0:
                return f"未找到股票 {stock_code} 在 {date} 的交易数据，可能是非交易日或数据未更新"

            # 获取最近的交易日期
            latest_date = conn.execute(text("""
                SELECT MAX(trade_date) as latest_date
                FROM stock_historical_quotes
                WHERE stock_code = :code
            """), {'code': stock_code}).fetchone()

            if latest_date and date > latest_date.latest_date.strftime('%Y-%m-%d'):
                return f"当前最新数据更新至 {latest_date.latest_date.strftime('%Y-%m-%d')}"

            # 先获取股票基本信息
            basic_info = conn.execute(text("""
                SELECT stock_code, stock_name
                FROM stocks
                WHERE stock_code = :code
            """), {'code': stock_code}).fetchone()

            if not basic_info:
                return f"未找到股票代码 {stock_code} 的信息"

            # 获取均线数据
            ma_result = conn.execute(text("""
                WITH RECURSIVE date_series AS (
                    SELECT MIN(trade_date) as date_range_start
                    FROM stock_historical_quotes
                    WHERE trade_date >= DATE_SUB(:date, INTERVAL 250 DAY)
                ),
                moving_averages AS (
                    SELECT 
                        stock_code,
                        trade_date,
                        close_price,
                        volume,
                        AVG(close_price) OVER (
                            PARTITION BY stock_code 
                            ORDER BY trade_date 
                            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        ) AS ma_5,
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
                            ROWS BETWEEN 99 PRECEDING AND CURRENT ROW
                        ) AS ma_100,
                        AVG(close_price) OVER (
                            PARTITION BY stock_code 
                            ORDER BY trade_date 
                            ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
                        ) AS ma_200
                    FROM stock_historical_quotes
                    WHERE stock_code = :code
                        AND trade_date >= (
                            SELECT date_range_start FROM date_series
                        )
                )
                SELECT *
                FROM moving_averages
                WHERE trade_date = :date
            """), {'code': stock_code, 'date': date}).fetchone()

            if not ma_result:
                return f"未能计算股票 {stock_code} 在 {date} 的均线数据，可能历史数据不足"

            # 获取成交量数据和均线
            volume_result = conn.execute(text("""
                WITH RECURSIVE date_series AS (
                    SELECT MIN(trade_date) as date_range_start
                    FROM stock_historical_quotes
                    WHERE trade_date >= DATE_SUB(:date, INTERVAL 250 DAY)
                ),
                volume_averages AS (
                    SELECT 
                        stock_code,
                        trade_date,
                        volume,
                        AVG(volume) OVER (
                            PARTITION BY stock_code 
                            ORDER BY trade_date 
                            ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
                        ) AS volume_ma5,
                        AVG(volume) OVER (
                            PARTITION BY stock_code 
                            ORDER BY trade_date 
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) AS volume_ma20,
                        AVG(volume) OVER (
                            PARTITION BY stock_code 
                            ORDER BY trade_date 
                            ROWS BETWEEN 59 PRECEDING AND CURRENT ROW
                        ) AS volume_ma60,
                        AVG(volume) OVER (
                            PARTITION BY stock_code 
                            ORDER BY trade_date 
                            ROWS BETWEEN 99 PRECEDING AND CURRENT ROW
                        ) AS volume_ma100,
                        AVG(volume) OVER (
                            PARTITION BY stock_code 
                            ORDER BY trade_date 
                            ROWS BETWEEN 199 PRECEDING AND CURRENT ROW
                        ) AS volume_ma200
                    FROM stock_historical_quotes
                    WHERE stock_code = :code
                        AND trade_date >= (
                            SELECT date_range_start FROM date_series
                        )
                )
                SELECT *
                FROM volume_averages
                WHERE trade_date = :date
            """), {'code': stock_code, 'date': date}).fetchone()

            if not volume_result:
                return f"未能获取股票 {stock_code} 在 {date} 的成交量数据"

            # 获取三连阳数据
            bullish_result = conn.execute(text("""
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
                        ((c.close_price - c.open_price) / c.open_price * 100) as today_gain,
                        ((p1.close_price - p1.open_price) / p1.open_price * 100) as prev1_gain,
                        ((p2.close_price - p2.open_price) / p2.open_price * 100) as prev2_gain,
                        ((c.close_price - p2.open_price) / p2.open_price * 100) as total_gain,
                        CASE WHEN c.close_price > c.open_price THEN 1 ELSE 0 END as today_bullish,
                        CASE WHEN p1.close_price > p1.open_price THEN 1 ELSE 0 END as prev1_bullish,
                        CASE WHEN p2.close_price > p2.open_price THEN 1 ELSE 0 END as prev2_bullish
                    FROM continuous_trading_days t
                    JOIN stock_historical_quotes c ON t.stock_code = c.stock_code 
                        AND t.cur_date = c.trade_date
                    LEFT JOIN stock_historical_quotes p1 ON t.stock_code = p1.stock_code 
                        AND t.prev_date1 = p1.trade_date
                    LEFT JOIN stock_historical_quotes p2 ON t.stock_code = p2.stock_code 
                        AND t.prev_date2 = p2.trade_date
                )
                SELECT 
                    stock_code,
                    trade_date,
                    CASE 
                        WHEN today_bullish = 1 AND prev1_bullish = 1 AND prev2_bullish = 1 
                        THEN '三连阳'
                        ELSE '非三连阳'
                    END as pattern_type,
                    total_gain
                FROM three_days_data
            """), {'code': stock_code, 'date': date}).fetchone()

            # 获取吞没形态数据
            engulfing_result = conn.execute(text("""
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
                        p.open_price AS prev_open,
                        p.close_price AS prev_close
                    FROM continuous_trading_days t
                    JOIN stock_historical_quotes c ON t.stock_code = c.stock_code 
                        AND t.cur_date = c.trade_date
                    JOIN stock_historical_quotes p ON t.stock_code = p.stock_code 
                        AND t.prev_date = p.trade_date
                )
                SELECT 
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
            """), {'code': stock_code, 'date': date}).fetchone()

            # 获取支撑阻力位数据
            support_result = conn.execute(text("""
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
                            WHEN close_price > vwap_20d THEN '高于加权均价'
                            ELSE '低于加权均价'
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
                            WHEN close_price >= (max_price_20d + min_price_20d) / 2 THEN '价格区间上半部'
                            ELSE '价格区间下半部'
                        END AS price_range_position,
                        CASE
                            WHEN volume > avg_volume_20d * 1.5 THEN '放量'
                            WHEN volume < avg_volume_20d * 0.7 THEN '缩量'
                            ELSE '量能一般'
                        END AS volume_character
                    FROM price_levels
                )
                SELECT * FROM support_resistance_analysis
                WHERE trade_date = :date
            """), {'code': stock_code, 'date': date}).fetchone()

            # 获取均线交叉数据
            cross_result = conn.execute(text("""
                WITH moving_averages AS (
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
                    *,
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
                    END AS cross_type
                FROM crossover_analysis
                WHERE trade_date = :date
            """), {'code': stock_code, 'date': date}).fetchone()

        # 2. 构建AI分析的prompt
        analysis_prompt = f"""
        股票代码：{basic_info.stock_code}
        股票名称：{basic_info.stock_name}
        分析日期：{date}

        我已经基于以下 SQL 策略计算出技术指标，请结合这些指标分析股票趋势和交易信号：
        技术指标
        1. 均线分析：
          - MA5=${ma_result.ma_5:.2f}
          - MA20=${ma_result.ma_20:.2f}
          - MA60=${ma_result.ma_60:.2f}
          - MA100=${ma_result.ma_100:.2f}
          - MA200=${ma_result.ma_200:.2f}
          - 均线交叉：{cross_result.cross_type}
          - 交叉强度：{cross_result.cross_strength:.2f}%
          - MA5变化率：{cross_result.ma_5_change:.2f}%
          - MA20变化率：{cross_result.ma_20_change:.2f}%
        2. 成交量分析：
          - 当前成交量：{volume_result.volume/10000:.2f}万手
          - 5日均量：{volume_result.volume_ma5/10000:.2f}万手
          - 20日均量：{volume_result.volume_ma20/10000:.2f}万手
          - 60日均量：{volume_result.volume_ma60/10000:.2f}万手
          - 100日均量：{volume_result.volume_ma100/10000:.2f}万手
          - 200日均量：{volume_result.volume_ma200/10000:.2f}万手
          - 量比（当前/20日均量）：{(volume_result.volume/volume_result.volume_ma20):.2f}
        5. K线形态：
          - 最近3日{bullish_result.pattern_type}，累计涨幅{bullish_result.total_gain:.2f}%。
          - 今日吞没形态：{engulfing_result.engulfing_type or '无形态'}。
        6. 支撑与阻力：
          - 5日支撑位：${support_result.min_price_5d:.2f}
          - 10日支撑位：${support_result.min_price_10d:.2f}
          - 20日支撑位：${support_result.min_price_20d:.2f}
          - 5日阻力位：${support_result.max_price_5d:.2f}
          - 10日阻力位：${support_result.max_price_10d:.2f}
          - 20日阻力位：${support_result.max_price_20d:.2f}
          - 20日加权均价：${support_result.vwap_20d:.2f}
          - 支撑强度：{support_result.support_strength}
          - 阻力强度：{support_result.resistance_strength}
          - 价格位置：{support_result.price_position}
          - 区间位置：{support_result.price_range_position}
          - 量能特征：{support_result.volume_character}

        分析需求
        1. 趋势分析：判断当前股票是处于多头、空头还是震荡行情。
        2. 交易信号：
          - 如果均线呈现金叉形态（如 MA5 上穿 MA20），并且成交量较 20 日均线放大 50%，建议买入。
          - 如果股价接近阻力位，且成交量缩量至 20 日均量以下，建议卖出。
          - 如果无明显趋势，且波动幅度小于2%，建议观望。
        3. 风险评估：
          - 包括支撑与阻力的有效性评估。
          - 分析市场波动性及潜在回撤。
        4. 潜在收益分析：结合当前价格和历史阻力位，估算可能的收益空间。
        5. 投资策略与执行建议：
          - 提供具体的买入或卖出时机。
          - 若无明显信号，建议观察哪些关键指标变化。

        输出格式（json格式）
        - 趋势判断：如多头、空头或震荡。
        - 交易信号：买入、卖出或观望。
        - 分析依据：结合指标，列举支撑信号的具体数据和逻辑。
        - 风险评估：分析潜在风险和对策。
        - 收益分析：提供合理的目标价和预期收益。
        - 执行建议：具体的操作建议和触发条件。
        """

        # 3. 调用AI接口
        analyzer = AIAnalyzer()
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一位金融分析助手，精通股票市场趋势、基本面分析、技术分析和风险评估。"
                    "我会给你中国A股股票的分析数据，股票价格都是人民币，同时你的回答应该使用中文，并提供清晰且专业的建议。"
                )
            },
            {
                "role": "user",
                "content": analysis_prompt
            }
        ]
        
        try:
            analysis_result = analyzer.get_analysis(messages)
            logger.info(f"分析完成: {stock_code}")
            return analysis_result
        except Exception as e:
            logger.error(f"AI分析最终失败: {str(e)}")
            return f"很抱歉，AI分析服务暂时不可用，请稍后再试。"

    except Exception as e:
        logger.error(f"获取技术分析失败: {str(e)}")
        return str(e)

@ai_analysis_bp.route('/analysis/<stock_code>', methods=['GET'])
def get_ai_analysis(stock_code):
    """获取 AI 技术分析"""
    try:
        date = request.args.get('date', type=str)
        if not date:
            return jsonify({'error': '日期不能为空'}), 400
            
        # 添加日志
        logger.info(f"开始分析股票 {stock_code}, 日期 {date}")
            
        # 调用 AI 分析函数
        analysis_result = get_technical_analysis(stock_code, date)
        
        # 检查结果
        if not analysis_result:
            return jsonify({'error': '分析结果为空'}), 500
            
        response_data = {
            'stock_code': stock_code,
            'analysis_date': date,
            'analysis': analysis_result
        }
        
        # 添加日志
        logger.info(f"分析完成: {stock_code}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取AI回答失败: {str(e)}")
        return jsonify({'error': str(e)}), 500 