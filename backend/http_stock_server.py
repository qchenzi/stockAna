from flask import Flask
import logging
from apis.technical_api import technical_bp
from apis.stock_details_api import details_bp
from apis.stock_ai_analysis_api import ai_analysis_bp
from apis.stock_history_api import history_bp
from apis.stock_recommendation_api import recommendation_bp
from apis.stock_technical_score_api import technical_score_bp
from apis.chip_analysis_api import chip_analysis_bp

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

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Stock Analysis Server')
    parser.add_argument('--port', type=int, default=5000, help='服务器端口号 (默认: 5000)')
    
    args = parser.parse_args()
    app.run(host='0.0.0.0', port=args.port, debug=True)