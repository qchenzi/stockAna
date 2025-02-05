from flask import Blueprint, request, jsonify
from sqlalchemy import text, create_engine
from config.database import DB_CONFIG_READER
from decimal import Decimal

technical_score_bp = Blueprint('technical_score', __name__)

engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG_READER['user']}:{DB_CONFIG_READER['password']}"
    f"@{DB_CONFIG_READER['host']}/{DB_CONFIG_READER['database']}?charset=utf8mb4"
)

@technical_score_bp.route('/scores', methods=['GET'])
def get_technical_scores():
    """获取股票技术评分排名"""
    date = request.args.get('date')
    limit = request.args.get('limit', default=50, type=int)
    
    try:
        with engine.connect() as conn:
            if date:
                # 获取指定日期的评分排名
                result = conn.execute(text("""
                    SELECT s.stock_code, s.stock_name, s.industry,
                           ts.total_score, ts.trend_score, ts.momentum_score, 
                           ts.volatility_score, ts.volume_score, ts.bollinger_score,
                           ts.ma5, ts.ma20, ts.ma60, ts.vol_ma5, ts.vol_ma20,
                           ts.volatility, ts.boll_upper, ts.boll_lower,
                           ts.macd, ts.macd_signal,
                           q.close_price,
                           q.change_ratio
                    FROM stock_technical_scores ts
                    JOIN stocks s ON ts.stock_code = s.stock_code
                    JOIN stock_historical_quotes q ON ts.stock_code = q.stock_code 
                        AND DATE(ts.score_date) = DATE(q.trade_date)
                    WHERE DATE(ts.score_date) = DATE(:date)
                    ORDER BY ts.total_score DESC
                    LIMIT :limit
                """), {'date': date, 'limit': limit}).fetchall()
            else:
                # 获取最新日期的评分排名
                result = conn.execute(text("""
                    SELECT s.stock_code, s.stock_name, s.industry,
                           ts.total_score, ts.trend_score, ts.momentum_score, 
                           ts.volatility_score, ts.volume_score, ts.bollinger_score,
                           ts.ma5, ts.ma20, ts.ma60, ts.vol_ma5, ts.vol_ma20,
                           ts.volatility, ts.boll_upper, ts.boll_lower,
                           ts.macd, ts.macd_signal,
                           q.close_price,
                           q.change_ratio
                    FROM stock_technical_scores ts
                    JOIN stocks s ON ts.stock_code = s.stock_code
                    JOIN stock_historical_quotes q ON ts.stock_code = q.stock_code 
                        AND DATE(ts.score_date) = DATE(q.trade_date)
                    WHERE DATE(ts.score_date) = (
                        SELECT DATE(MAX(score_date)) FROM stock_technical_scores
                    )
                    ORDER BY ts.total_score DESC
                    LIMIT :limit
                """), {'limit': limit}).fetchall()

            scores = [{
                'stock_code': row.stock_code,
                'stock_name': row.stock_name,
                'industry': row.industry,
                'current_price': float(row.close_price),
                'change_ratio': float(row.change_ratio),
                'total_score': row.total_score,
                # 趋势分析
                'trend_analysis': {
                    'score': row.trend_score,
                    'ma5': float(row.ma5),
                    'ma20': float(row.ma20),
                    'ma60': float(row.ma60),
                    'status': '强势上涨' if row.ma5 > row.ma20 and row.ma20 > row.ma60 else 
                             '短期向好' if row.ma5 > row.ma20 else 
                             '盘整' if float(row.close_price) > row.ma20 else '弱势'
                },
                # 动量分析
                'momentum_analysis': {
                    'score': row.momentum_score,
                    'macd': float(row.macd),
                    'macd_signal': float(row.macd_signal),
                    'status': 'MACD金叉' if row.macd > row.macd_signal else 'MACD死叉'
                },
                # 成交量分析
                'volume_analysis': {
                    'score': row.volume_score,
                    'vol_ma5': float(row.vol_ma5),
                    'vol_ma20': float(row.vol_ma20),
                    'status': '放量' if Decimal(str(row.vol_ma5)) > Decimal(str(row.vol_ma20)) * Decimal('1.2') else 
                             '缩量' if Decimal(str(row.vol_ma5)) < Decimal(str(row.vol_ma20)) * Decimal('0.8') else '正常'
                },
                # 波动率分析
                'volatility_analysis': {
                    'score': row.volatility_score,
                    'volatility': float(row.volatility),
                    'status': '剧烈波动' if Decimal(str(row.volatility)) > Decimal('3') else 
                             '中等波动' if Decimal(str(row.volatility)) > Decimal('1.5') else '平稳'
                },
                # 布林带分析
                'bollinger_analysis': {
                    'score': row.bollinger_score,
                    'upper': float(row.boll_upper),
                    'lower': float(row.boll_lower),
                    'status': '超买' if float(row.close_price) > float(row.boll_upper) else 
                             '超卖' if float(row.close_price) < float(row.boll_lower) else '正常'
                }
            } for row in result]

            return jsonify({
                'date': date,
                'scores': scores
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500 