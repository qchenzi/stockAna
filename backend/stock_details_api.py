from flask import Blueprint, jsonify, request
from sqlalchemy import text
import logging
from config.database import DB_CONFIG_READER
from sqlalchemy import create_engine

# 创建蓝图
details_bp = Blueprint('details', __name__)

# 配置日志
logger = logging.getLogger(__name__)

# 创建数据库连接
engine = create_engine(
    f"mysql+pymysql://{DB_CONFIG_READER['user']}:{DB_CONFIG_READER['password']}"
    f"@{DB_CONFIG_READER['host']}/{DB_CONFIG_READER['database']}?charset=utf8mb4"
)

@details_bp.route('/<stock_code>/details', methods=['GET'])
def get_stock_details(stock_code):
    """获取股票详情"""
    logger.info(f"开始获取股票详情, 代码: {stock_code}")
    
    try:
        # 1. 基本信息
        basic_sql = """
        SELECT 
            s.stock_code,
            s.stock_name,
            s.sector,
            s.industry,
            s.description,
            s.listing_date,
            s.website,
            s.employees
        FROM stocks s
        WHERE s.stock_code = :code
        """
        
        # 2. 最新交易数据
        quote_sql = """
        SELECT 
            trade_date,
            open_price,
            close_price,
            high_price,
            low_price,
            volume,
            amount
        FROM stock_historical_quotes
        WHERE stock_code = :code
        ORDER BY trade_date DESC
        LIMIT 1
        """
        
        # 3. 技术指标
        technical_sql = """
        SELECT 
            current_price,
            high_52week,
            low_52week,
            avg_volume,
            ma_200,
            beta
        FROM technical_metrics
        WHERE stock_code = :code
        ORDER BY date DESC
        LIMIT 1
        """
        
        # 4. 基本面指标
        fundamental_sql = """
        SELECT 
            pe_ratio,
            pb_ratio,
            roe,
            revenue_growth,
            earnings_growth,
            dividend_yield
        FROM fundamental_metrics
        WHERE stock_code = :code
        ORDER BY date DESC
        LIMIT 1
        """
        
        # 5. 财务健康
        financial_sql = """
        SELECT 
            quick_ratio,
            current_ratio,
            debt_to_equity,
            operating_cash_flow
        FROM financial_health
        WHERE stock_code = :code
        ORDER BY report_date DESC
        LIMIT 1
        """
        
        # 6. 机构持股
        investor_sql = """
        SELECT 
            insider_holding,
            institution_holding
        FROM investor_metrics
        WHERE stock_code = :code
        ORDER BY date DESC
        LIMIT 1
        """

        with engine.connect() as conn:
            basic_info = conn.execute(text(basic_sql), {'code': stock_code}).fetchone()
            logger.info(f"基本信息查询结果: {basic_info}")
            
            quote_data = conn.execute(text(quote_sql), {'code': stock_code}).fetchone()
            logger.info(f"行情数据查询结果: {quote_data}")
            
            technical_data = conn.execute(text(technical_sql), {'code': stock_code}).fetchone()
            logger.info(f"技术指标查询结果: {technical_data}")
            
            fundamental_data = conn.execute(text(fundamental_sql), {'code': stock_code}).fetchone()
            logger.info(f"基本面指标查询结果: {fundamental_data}")
            
            financial_data = conn.execute(text(financial_sql), {'code': stock_code}).fetchone()
            logger.info(f"财务健康查询结果: {financial_data}")
            
            investor_data = conn.execute(text(investor_sql), {'code': stock_code}).fetchone()
            logger.info(f"机构持股查询结果: {investor_data}")
            
        if not basic_info:
            logger.warning(f"未找到股票信息: {stock_code}")
            return jsonify({'error': '未找到股票信息'}), 404

        def safe_float(value):
            """安全转换为浮点数"""
            try:
                return float(value) if value is not None else None
            except (TypeError, ValueError):
                return None

        response_data = {
            'basic': {
                'code': basic_info.stock_code,
                'name': basic_info.stock_name,
                'sector': basic_info.sector,
                'industry': basic_info.industry,
                'description': basic_info.description,
                'listingDate': basic_info.listing_date.strftime('%Y-%m-%d') if basic_info.listing_date else None,
                'website': basic_info.website,
                'employees': basic_info.employees
            },
            'quote': {
                'date': quote_data.trade_date.strftime('%Y-%m-%d') if quote_data else None,
                'open': safe_float(quote_data.open_price if quote_data else None),
                'close': safe_float(quote_data.close_price if quote_data else None),
                'high': safe_float(quote_data.high_price if quote_data else None),
                'low': safe_float(quote_data.low_price if quote_data else None),
                'volume': safe_float(quote_data.volume if quote_data else None),
                'amount': safe_float(quote_data.amount if quote_data else None)
            },
            'technical': {
                'currentPrice': safe_float(technical_data.current_price if technical_data else None),
                'high52Week': safe_float(technical_data.high_52week if technical_data else None),
                'low52Week': safe_float(technical_data.low_52week if technical_data else None),
                'avgVolume': safe_float(technical_data.avg_volume if technical_data else None),
                'ma200': safe_float(technical_data.ma_200 if technical_data else None),
                'beta': safe_float(technical_data.beta if technical_data else None)
            },
            'fundamental': {
                'peRatio': safe_float(fundamental_data.pe_ratio if fundamental_data else None),
                'pbRatio': safe_float(fundamental_data.pb_ratio if fundamental_data else None),
                'roe': safe_float(fundamental_data.roe if fundamental_data else None),
                'revenueGrowth': safe_float(fundamental_data.revenue_growth if fundamental_data else None),
                'earningsGrowth': safe_float(fundamental_data.earnings_growth if fundamental_data else None),
                'dividendYield': safe_float(fundamental_data.dividend_yield if fundamental_data else None)
            },
            'financial': {
                'quickRatio': safe_float(financial_data.quick_ratio if financial_data else None),
                'currentRatio': safe_float(financial_data.current_ratio if financial_data else None),
                'debtToEquity': safe_float(financial_data.debt_to_equity if financial_data else None),
                'operatingCashFlow': safe_float(financial_data.operating_cash_flow if financial_data else None)
            },
            'investor': {
                'insiderHolding': safe_float(investor_data.insider_holding if investor_data else None),
                'institutionHolding': safe_float(investor_data.institution_holding if investor_data else None)
            }
        }
        
        logger.info(f"返回数据: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取股票详情失败: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500 

@details_bp.route('/search', methods=['GET'])
def search_stocks():
    """搜索股票"""
    keyword = request.args.get('keyword', '')
    if not keyword:
        return jsonify([])
    
    try:
        with engine.connect() as conn:
            sql = """
            SELECT stock_code as code, stock_name as name
            FROM stocks
            WHERE stock_code LIKE :keyword
            OR stock_name LIKE :keyword
            LIMIT 50
            """
            results = conn.execute(
                text(sql), 
                {'keyword': f'%{keyword}%'}
            ).fetchall()
            
            return jsonify([
                {'code': row.code, 'name': row.name}
                for row in results
            ])
    except Exception as e:
        logger.error(f"搜索股票失败: {str(e)}")
        return jsonify({'error': str(e)}), 500 

@details_bp.route('/<stock_code>/latest-trade-date', methods=['GET'])
def get_latest_trade_date(stock_code):
    """获取股票最新交易日期"""
    try:
        with engine.connect() as conn:
            sql = """
            SELECT trade_date
            FROM stock_historical_quotes
            WHERE stock_code = :code
            ORDER BY trade_date DESC
            LIMIT 1
            """
            result = conn.execute(text(sql), {'code': stock_code}).fetchone()
            
            if not result:
                return jsonify({'error': '未找到交易数据'}), 404
                
            return jsonify({
                'date': result.trade_date.strftime('%Y-%m-%d')
            })
            
    except Exception as e:
        logger.error(f"获取最新交易日期失败: {str(e)}")
        return jsonify({'error': str(e)}), 500