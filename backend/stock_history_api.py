from flask import Blueprint, request, jsonify
from sqlalchemy import text, create_engine
from config.database import DB_CONFIG_READER

history_bp = Blueprint('history', __name__)

# 创建数据库连接
engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG_READER['user']}:{DB_CONFIG_READER['password']}"
    f"@{DB_CONFIG_READER['host']}/{DB_CONFIG_READER['database']}?charset=utf8mb4"
)

@history_bp.route('/stocks/<stock_code>/history', methods=['GET'])
def get_recent_history(stock_code):
    days = request.args.get('days', default=5, type=int)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    trade_date as date,
                    open_price as open,
                    close_price as close,
                    high_price as high,
                    low_price as low,
                    volume
                FROM stock_historical_quotes
                WHERE stock_code = :code
                ORDER BY trade_date DESC
                LIMIT :days
            """), {
                'code': stock_code,
                'days': days
            }).fetchall()
            
            history_data = [{
                'date': row.date.strftime('%Y-%m-%d'),
                'open': float(row.open),
                'close': float(row.close),
                'high': float(row.high),
                'low': float(row.low),
                'volume': int(row.volume)
            } for row in result]
            
            history_data.reverse()
            
            return jsonify(history_data)
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500 