from flask import Blueprint, request, jsonify
from sqlalchemy import text, create_engine
from config.database import DB_CONFIG_READER

recommendation_bp = Blueprint('recommendation', __name__)

# 创建数据库连接
engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG_READER['user']}:{DB_CONFIG_READER['password']}"
    f"@{DB_CONFIG_READER['host']}/{DB_CONFIG_READER['database']}?charset=utf8mb4"
)

@recommendation_bp.route('/recommendations', methods=['GET'])
def get_recommendations():
    # 获取请求的日期参数，如果没有则使用最新交易日
    requested_date = request.args.get('date')
    print("requested_date:" + (requested_date if requested_date else "None"))
    
    try:
        with engine.connect() as conn:
            if requested_date:
                # 检查请求的日期是否有数据
                result = conn.execute(text("""
                    SELECT recommend_date, stock_code, stock_name, industry, 
                           current_price, total_score, recommendation_level, reasons
                    FROM stock_recommendations
                    WHERE DATE(recommend_date) = DATE(:date)
                    ORDER BY total_score DESC
                """), {'date': requested_date}).fetchall()
                
                if not result:
                    # 如果没有找到数据，返回404
                    return jsonify({
                        'error': f'No data available for {requested_date}',
                        'available_dates': get_available_dates(conn)
                    }), 404
            else:
                # 获取最新的推荐日期和数据
                result = conn.execute(text("""
                    SELECT recommend_date, stock_code, stock_name, industry, 
                           current_price, total_score, recommendation_level, reasons
                    FROM stock_recommendations
                    WHERE DATE(recommend_date) = (
                        SELECT DATE(MAX(recommend_date)) 
                        FROM stock_recommendations
                    )
                    ORDER BY total_score DESC
                """)).fetchall()

            recommendations = [{
                'recommend_date': row.recommend_date.strftime('%Y-%m-%d'),
                'stock_code': row.stock_code,
                'stock_name': row.stock_name,
                'industry': row.industry,
                'current_price': float(row.current_price),
                'total_score': row.total_score,
                'recommendation_level': row.recommendation_level,
                'reasons': row.reasons
            } for row in result]

            return jsonify({
                'date': recommendations[0]['recommend_date'] if recommendations else None,
                'recommendations': recommendations
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_available_dates(conn):
    """获取所有可用的推荐日期"""
    result = conn.execute(text("""
        SELECT DISTINCT DATE(recommend_date) as date
        FROM stock_recommendations
        ORDER BY date DESC
        LIMIT 10
    """)).fetchall()
    return [row.date.strftime('%Y-%m-%d') for row in result] 