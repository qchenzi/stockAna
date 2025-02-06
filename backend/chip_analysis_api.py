from flask import Blueprint, request, jsonify
from sqlalchemy import text, create_engine
from config.database import DB_CONFIG_READER
from decimal import Decimal
import datetime

chip_analysis_bp = Blueprint('chip_analysis', __name__)

# 策略类型映射
STRATEGY_TYPE_MAP = {
    'buy_dip': '低吸',
    'follow_up': '追涨',
    'potential': '潜力'
}

engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG_READER['user']}:{DB_CONFIG_READER['password']}"
    f"@{DB_CONFIG_READER['host']}/{DB_CONFIG_READER['database']}?charset=utf8mb4"
)

@chip_analysis_bp.route('/api/chip/analysis', methods=['GET'])
def get_chip_analysis():
    try:
        # 获取请求参数
        date = request.args.get('date', '')
        strategy_type_en = request.args.get('type', 'buy_dip')
        
        # 将英文类型转换为数据库中的中文
        strategy_type = STRATEGY_TYPE_MAP.get(strategy_type_en, '低吸')
        
        # 添加调试日志
        print(f"Request params - date: {date}, type: {strategy_type_en}")
        print(f"Converted strategy type: {strategy_type}")
        print(f"Strategy type map: {STRATEGY_TYPE_MAP}")
        
        with engine.connect() as conn:
            # 如果没有指定日期，获取最新的分析日期
            if not date:
                date_query = text("""
                    SELECT MAX(analysis_date) as latest_date 
                    FROM stock_chip_analysis
                """)
                result = conn.execute(date_query).fetchone()
                date = result[0].strftime('%Y-%m-%d') if result[0] else None
                print(f"Latest date from DB: {date}")
                
                if not date:
                    return jsonify({'error': '无分析数据'}), 404

            # 先检查数据是否存在
            check_query = text("""
                SELECT COUNT(*) as count, strategy_type
                FROM stock_chip_analysis
                WHERE analysis_date = :date
                AND strategy_type = :type
                GROUP BY strategy_type
            """)
            
            check_result = conn.execute(check_query, {
                'date': date,
                'type': strategy_type
            }).fetchone()
            
            print(f"Check query params - date: {date}, type: {strategy_type}")
            print(f"Check query result: {check_result}")
            
            if not check_result:
                # 列出该日期所有可用的策略类型
                available_types_query = text("""
                    SELECT DISTINCT strategy_type
                    FROM stock_chip_analysis
                    WHERE analysis_date = :date
                """)
                available_types = [row[0] for row in conn.execute(available_types_query, {'date': date}).fetchall()]
                print(f"Available strategy types for date {date}: {available_types}")
                return jsonify({'error': '所选日期无数据'}), 404

            count = check_result[0]
            print(f"Found {count} records")

            # 根据策略类型获取股票列表
            query = text("""
                SELECT 
                    sca.stock_code,
                    sca.stock_name,
                    sca.industry,
                    sca.close_price,
                    sca.ma60,
                    sca.vwap,
                    sca.main_chip_ratio,
                    sca.profit_chip_ratio,
                    sca.locked_chip_ratio,
                    sca.floating_chip_ratio,
                    sca.rank_num
                FROM stock_chip_analysis sca
                WHERE sca.analysis_date = :date
                AND sca.strategy_type = :type
                ORDER BY sca.rank_num ASC
                LIMIT 50
            """)
            
            result = conn.execute(query, {
                'date': date,
                'type': strategy_type
            }).fetchall()

            # 格式化返回数据
            stocks = [{
                'stock_code': row.stock_code,
                'stock_name': row.stock_name,
                'industry': row.industry,
                'close_price': str(row.close_price),
                'ma60': str(row.ma60),
                'vwap': str(row.vwap),
                'main_chip_ratio': float(row.main_chip_ratio),
                'main_chip_ratio_display': '{:.2f}'.format(float(row.main_chip_ratio) * 100),
                'profit_chip_ratio': float(row.profit_chip_ratio),
                'profit_chip_ratio_display': '{:.2f}'.format(float(row.profit_chip_ratio) * 100),
                'locked_chip_ratio': float(row.locked_chip_ratio),
                'locked_chip_ratio_display': '{:.2f}'.format(float(row.locked_chip_ratio) * 100),
                'floating_chip_ratio': float(row.floating_chip_ratio),
                'floating_chip_ratio_display': '{:.2f}'.format(float(row.floating_chip_ratio) * 100),
                'rank_num': row.rank_num
            } for row in result]

            return jsonify({
                'date': date,
                'stocks': stocks
            })
            
    except Exception as e:
        print(f"Error in chip analysis API: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': '服务器内部错误'}), 500 