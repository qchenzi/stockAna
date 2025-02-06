from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text
from config.database import DB_CONFIG_READER
import logging
import subprocess
import json
from datetime import datetime
import math
from technical_api import technical_bp
from stock_details_api import details_bp
from stock_ai_analysis_api import ai_analysis_bp
from stock_history_api import history_bp
from stock_recommendation_api import recommendation_bp
from stock_technical_score_api import technical_score_bp
from chip_analysis_api import chip_analysis_bp

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 注册所有蓝图
app.register_blueprint(technical_bp, url_prefix='/api/technical')
app.register_blueprint(details_bp, url_prefix='/api/stocks')
app.register_blueprint(ai_analysis_bp, url_prefix='/api/ai')
app.register_blueprint(history_bp, url_prefix='/api')
app.register_blueprint(recommendation_bp, url_prefix='/api/technical')
app.register_blueprint(technical_score_bp, url_prefix='/api/technical')
app.register_blueprint(chip_analysis_bp)

# 创建数据库连接
engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG_READER['user']}:{DB_CONFIG_READER['password']}"
    f"@{DB_CONFIG_READER['host']}/{DB_CONFIG_READER['database']}?charset=utf8mb4"
)

# 在文件开头添加策略说明定义
strategy_descriptions = {
    'rtpv': 'RTPV综合策略 - 多因子选股',
    'value': '价值投资策略 - 基本面选股',
    'growth': '成长精选策略 - 高成长性选股',
    'income': '稳健收益策略 - 高分红低波动',
    'trend': '趋势动量策略 - 技术指标选股',
    'reverse': '反转机会策略 - 超跌反弹选股'
}

# 自定义 JSON 编码器处理 NaN 值
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and math.isnan(obj):
            return None  # 将 NaN 转换为 null
        return super().default(obj)

# 简化策略名称
strategy_names = {
    'rtpv': 'RTPV综合策略',
    'value': '价值投资策略',
    'growth': '成长精选策略',
    'income': '稳健收益策略',
    'trend': '趋势动量策略',
    'reverse': '反转机会策略'
}

@app.route('/api/stocks/<strategy>', methods=['GET'])
def get_stocks_by_strategy(strategy):
    """获取指定策略的股票列表"""
    try:
        # 获取参数
        top = request.args.get('top', default=20, type=int)
        date = request.args.get('date', default=None)
        period = request.args.get('period', default=14, type=int)  # 默认改为14天
        
        # 获取最近的交易日
        sql = """
        SELECT MAX(date) as latest_date 
        FROM fundamental_metrics
        """
        if date:
            sql += f" WHERE date <= '{date}'"
        else:
            sql += " WHERE date <= CURRENT_DATE"
            
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            latest_date = result.scalar()
            
        if not latest_date:
            logger.error("没有找到有效的交易日数据")
            return app.response_class(
                response=json.dumps(
                    {'error': '没有找到有效的交易日数据'},
                    ensure_ascii=False
                ),
                status=404,
                mimetype='application/json'
            )
            
        # 使用最近的交易日
        date = latest_date.strftime('%Y-%m-%d')
        logger.info(f"使用交易日期: {date}")
        
        # 执行评分命令
        cmd = f'python3 sh_stock_scorer.py --strategy {strategy} --top {top} --date {date}'
        if strategy == 'rtpv':
            cmd += f' --period {period}'
            
        logger.info(f"执行命令: {cmd}")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # 记录原始输出
        output = result.stdout
        error_output = result.stderr
        logger.info(f"命令输出: {output}")
        if error_output:
            logger.error(f"命令错误: {error_output}")

        if not output:
            return app.response_class(
                response=json.dumps(
                    {'error': '评分计算失败', 'stderr': error_output},
                    ensure_ascii=False
                ),
                status=500,
                mimetype='application/json'
            )

        # 解析输出
        lines = output.split('\n')
        
        # 定义所有策略的评分规则
        all_scoring_rules = {
            'rtpv': [
                "1. ROE(30分):        >0%得30分，>0%得20分，其他得10分",
                "2. RSI(30分):        50-80得40分，40-90得20分，其他得0分",
                "3. 价格变动(30分):   价格变动百分比>0%得30分，>0%得20分，其他得10分",
                "4. 成交量比(10分):   >1得10分，>0.5得5分",
                "",
                "指标说明：",
                "ROE：        净资产收益率，反映公司盈利能力",
                "RSI：        相对强弱指标，衡量股价超买超卖程度",
                "价格变动：   近期股价涨跌幅度",
                "量比：       当日成交量与过去10日平均成交量之比"
            ],
            'value': [
                "1. 市盈率(30分): 低于行业均值20%得30分，低于均值得20分，其他得10分",
                "2. 市净率(20分): <3倍得20分，<5倍得10分",
                "3. ROE(30分): >15%得30分，>10%得20分，其他得10分",
                "4. 毛利率(10分): >40%得10分，>30%得5分",
                "5. 行业排名(10分): 前5名得10分，前10名得5分",
                "",
                "指标说明:",
                "PE: 市盈率，反映股票估值水平",
                "ROE: 净资产收益率，反映公司盈利能力",
                "毛利率: 营业收入减去营业成本的比率，反映产品盈利能力",
                "市净率: 每股市值与每股净资产之比，反映股票估值水平"
            ],
            'growth': [
                "1. 营收增速(30分):   >30%得30分，>15%得20分，其他得10分",
                "2. 净利润增速(30分): >50%得30分，>25%得20分，其他得10分",
                "3. 技术趋势(20分):   股价高于200日均线得20分，高于50日均线得10分",
                "4. 流动性(20分):     流动比率>2得20分，>1.5得10分，其他得5分",
                "",
                "指标说明：",
                "营收增速：   公司营业收入的同比增长率",
                "净利润增速： 公司净利润的同比增长率",
                "技术趋势：   股价相对于均线的位置关系",
                "流动比率：   流动资产/流动负债，反映短期偿债能力"
            ],
            'income': [
                "1. 股息率(40分):     >5%得40分，>3%得20分，其他得10分",
                "2. 分红持续性(20分): 连续3年分红得20分，连续2年得10分",
                "3. 现金流(20分):     经营现金流>0得20分，>净利润得10分",
                "4. 波动率(20分):     低于行业均值得20分，接近均值得10分",
                "",
                "指标说明：",
                "股息率：     每股股息与股价的比率，反映投资收益率",
                "分红持续性： 公司持续分红的年限",
                "经营现金流： 经营活动产生的现金流量净额",
                "β：          贝塔系数，衡量股票相对大盘的波动性"
            ],
            'trend': [
                "1. 均线系统(30分):   站上所有均线得30分，部分均线之上得20分",
                "2. MACD(30分):       金叉得30分，即将金叉得15分",
                "3. 成交量(20分):     放量上涨得20分，缩量下跌得10分",
                "4. 相对强弱(20分):   强于大盘得20分，跟随大盘得10分",
                "",
                "指标说明：",
                "均线系统：   包括5日、10日、20日、60日等均线",
                "MACD：       指数平滑异同移动平均线，判断趋势",
                "RSI：        相对强弱指标，衡量股价超买超卖程度",
                "量比：       当日成交量与过去10日平均成交量之比"
            ],
            'reverse': [
                "1. 超跌程度(30分):   下跌超过50%得30分，下跌超过30%得20分",
                "2. 技术反转(30分):   出现反转信号得30分，蓄势待发得15分",
                "3. 资金流向(20分):   开始流入得20分，流出减缓得10分",
                "4. 基本面(20分):     基本面优秀得20分，基本面稳定得10分",
                "",
                "指标说明：",
                "超跌程度：   相对历史高点的跌幅",
                "技术反转：   MACD、KDJ等技术指标的反转信号",
                "资金流向：   主力资金净流入情况",
                "ROE：        净资产收益率，反映公司盈利能力"
            ]
        }

        # 构建响应数据
        response_data = {
            'summary': f"计算 {latest_date} 的{strategy_names.get(strategy, strategy)}:",
            'strategy_desc': strategy_names.get(strategy, ''),  # 直接使用策略名称
            'scoring_rules': all_scoring_rules.get(strategy, []),
            'stocks': []
        }

        # 处理命令输出
        for line in output.split('\n'):
            if not line.strip():
                continue
                
            try:
                # 解析股票数据
                code = line[:6]
                name = line[7:].split(':')[0]
                score = float(line.split('总分=')[1].split()[0])
                
                # 解析指标数据
                metrics = {}
                if '(' in line and ')' in line:
                    metrics_str = line[line.find('(')+1:line.find(')')]
                    for metric in metrics_str.split(', '):
                        if '=' in metric:
                            key, value = metric.split('=')
                            try:
                                metrics[key] = float(value.rstrip('%'))
                            except ValueError:
                                metrics[key] = value
                
                # 添加到股票列表中
                stock_info = {
                    'code': code,
                    'name': name,
                    'score': score,
                    'metrics': metrics
                }
                response_data['stocks'].append(stock_info)
            except Exception as e:
                logger.warning(f"解析股票行失败: {line}, 错误: {str(e)}")
                continue

        logger.info(f"处理完成，返回数据: {response_data}")
        response = app.response_class(
            response=json.dumps(
                response_data,
                ensure_ascii=False,
                cls=CustomJSONEncoder  # 使用自定义编码器
            ),
            status=200,
            mimetype='application/json'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"获取股票列表失败: {str(e)}")
        return app.response_class(
            response=json.dumps(
                {'error': str(e), 'command': cmd},
                ensure_ascii=False
            ),
            status=500,
            mimetype='application/json'
        )

@app.route('/test', methods=['GET'])
def test():
    """测试路由"""
    try:
        return jsonify({
            'status': 'ok',
            'message': 'Service is running',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        logger.error(f"Test route error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/strategies', methods=['GET'])
def get_strategies():
    """获取所有策略列表"""
    try:
        strategies = {
            'rtpv': {
                'name': 'RTPV综合策略',
                'key': 'rtpv',
                'desc': '基于ROE、技术趋势、估值和成交量的多因子选股策略，适合中长期投资。',
                'details': {
                    'summary': '该策略通过分析公司质地、技术形态、估值水平和市场活跃度等多个维度，筛选出具有投资价值的优质股票。',
                    'factors': [
                        'ROE - 衡量公司盈利能力',
                        'RSI - 判断股价超买超卖',
                        'Price/Volume - 评估价格趋势与交易活跃度',
                        'Industry Rank - 行业排名分析'
                    ]
                }
            },
            'value': {
                'name': '价值投资策略',
                'key': 'value',
                'desc': '基于PE、PB、ROE等基本面指标的价值投资策略，适合稳健投资者。',
                'details': {
                    'summary': '通过分析公司的基本面指标，寻找被市场低估的优质公司，关注企业的内在价值。',
                    'factors': [
                        'PE比率 - 股价与每股收益的比值',
                        'PB比率 - 股价与每股净资产的比值',
                        'ROE - 净资产收益率',
                        '毛利率 - 反映产品竞争力'
                    ]
                }
            },
            'growth': {
                'name': '成长精选策略',
                'key': 'growth',
                'desc': '聚焦高成长性公司，通过营收增速、净利润增速等指标筛选高成长标的。',
                'details': {
                    'summary': '重点关注企业的成长性指标，寻找具有持续成长潜力的优质公司。',
                    'factors': [
                        '营收增速 - 反映业务扩张能力',
                        '净利润增速 - 体现盈利增长',
                        '研发投入 - 关注创新能力',
                        '市场份额 - 评估竞争地位'
                    ]
                }
            },
            'income': {
                'name': '稳健收益策略',
                'key': 'income',
                'desc': '专注高分红、低波动的价值型股票，适合追求稳定收益的投资者。',
                'details': {
                    'summary': '选择具有稳定现金流和良好分红记录的优质公司，平衡投资收益与风险。',
                    'factors': [
                        '股息率 - 衡量分红收益',
                        '分红历史 - 评估分红稳定性',
                        '现金流 - 分析经营稳健性',
                        '波动率 - 控制投资风险'
                    ]
                }
            },
            'trend': {
                'name': '趋势动量策略',
                'key': 'trend',
                'desc': '结合均线系统、MACD等技术指标，捕捉市场强势股票。',
                'details': {
                    'summary': '通过技术分析寻找市场强势股票，适合短中期交易。',
                    'factors': [
                        '均线系统 - 判断价格趋势',
                        'MACD - 识别趋势拐点',
                        '成交量 - 确认价格趋势',
                        '相对强弱 - 筛选强势股'
                    ]
                }
            },
            'reverse': {
                'name': '反转机会策略',
                'key': 'reverse',
                'desc': '寻找超跌反弹机会，通过技术指标捕捉市场情绪变化。',
                'details': {
                    'summary': '基于均值回归原理，在市场极端悲观时寻找投资机会，适合具有较强风险承受能力的投资者。',
                    'factors': [
                        '超跌程度 - 衡量价格偏离度',
                        '技术指标 - 判断反转信号',
                        '资金流向 - 跟踪市场情绪',
                        '基本面 - 确认投资价值'
                    ]
                }
            }
        }
        
        return app.response_class(
            response=json.dumps(
                {'strategies': strategies},
                ensure_ascii=False,
                indent=2
            ),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"获取策略列表失败: {str(e)}")
        return app.response_class(
            response=json.dumps(
                {'error': str(e)},
                ensure_ascii=False
            ),
            status=500,
            mimetype='application/json'
        )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 