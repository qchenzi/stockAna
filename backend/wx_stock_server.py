from flask import Flask, request
from sqlalchemy import create_engine, text
from config.database import DB_CONFIG_READER
import logging
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
import configparser

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 添加配置文件支持
config = configparser.ConfigParser()
config.read('config/server.ini')

# 微信配置
TOKEN = config.get('wx', 'token')

app = Flask(__name__)

class StockService:
    """股票服务类"""
    
    def __init__(self):
        self.engine = create_engine(
            f"mysql+pymysql://{DB_CONFIG_READER['user']}:{DB_CONFIG_READER['password']}"
            f"@{DB_CONFIG_READER['host']}/{DB_CONFIG_READER['database']}?charset=utf8mb4"
        )
        
        self.commands = {
            'help': self.show_help,
            'score': self.handle_score,
            'query': self.handle_query,
            'info': self.handle_info
        }

        # 策略映射
        self.strategy_map = {
            'score_rtpv': ('rtpv', 'RTPV综合策略'),
            'score_value': ('value', '价值投资策略'),
            'score_growth': ('growth', '成长投资策略'),
            'score_income': ('income', '收益投资策略'),
            'score_trend': ('trend', '趋势交易策略'),
            'score_reverse': ('reverse', '反向投资策略')
        }
    
    def show_help(self, user_id):
        """显示帮助信息"""
        return """股票分析助手使用说明：

1. 查看策略评分
发送: score <策略> [top数量]
策略可选: 
- rtpv (RTPV综合策略)
- value (价值投资策略)
- growth (成长投资策略)
- income (收益投资策略)
- trend (趋势交易策略)
- reverse (反向投资策略)

例如: 
score rtpv 10
score value 10

2. 查询个股信息（开发中）
发送: info <股票代码>
例如: info 600519

3. 条件查询（开发中）
发送: query <条件>
例如: 
query pe<30 roe>15
query dividend>5
query industry=科技

发送 help 显示本帮助
"""

    def handle_score(self, user_id, args):
        """处理评分请求"""
        try:
            if not args:
                return "请指定策略名称，例如: score rtpv 10"
                
            strategy = args[0]
            top = int(args[1]) if len(args) > 1 else 10
            
            # 获取最近的交易日
            sql = """
            SELECT MAX(date) as latest_date 
            FROM fundamental_metrics
            """
            
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                latest_date = result.scalar()
                
            if not latest_date:
                return "没有找到有效的交易日数据"
                
            # 使用最近的交易日
            date = latest_date.strftime('%Y-%m-%d')
            logger.info(f"使用交易日期: {date}")
            
            # 执行评分命令
            cmd = f'python3 sh_stock_scorer.py --strategy {strategy} --top {top} --date {date}'
            if strategy == 'rtpv':
                cmd += f' --period 14'
                
            logger.info(f"执行命令: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            # 记录原始输出
            output = result.stdout
            error_output = result.stderr
            logger.info(f"命令输出: {output}")
            if error_output:
                logger.error(f"命令错误: {error_output}")

            if not output:
                return "评分计算失败，请稍后重试"

            # 解析输出
            lines = output.split('\n')
            formatted_output = []
            section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('计算'):
                    formatted_output.append(line)
                elif line == '指标说明:':
                    formatted_output.append("\n指标说明:")
                    section = 'indicators'
                elif line == '评分标准:':
                    formatted_output.append("\n评分标准:")
                    section = 'rules'
                elif line == '评分前20名股票:':
                    formatted_output.append("\n评分结果:")
                    section = 'stocks'
                elif section == 'indicators' and line.startswith('- '):
                    formatted_output.append(line)
                elif section == 'rules' and line[0].isdigit():
                    formatted_output.append(line)
                elif section == 'stocks' and ':' in line:
                    formatted_output.append(line)

            return "\n".join(formatted_output)
            
        except Exception as e:
            logger.error(f"评分出错: {str(e)}")
            return "处理出错，请稍后重试"

    def handle_query(self, user_id, args):
        """处理条件查询"""
        return "条件查询功能开发中..."
    
    def handle_info(self, user_id, args):
        """处理个股信息查询"""
        return "个股信息查询功能开发中..."

    def handle_menu_click(self, user_id, event_key):
        """处理菜单点击事件"""
        try:
            if event_key in self.strategy_map:
                strategy, strategy_name = self.strategy_map[event_key]
                return self.handle_score(user_id, [strategy, '10'])
            return self.show_help(user_id)
        except Exception as e:
            logger.error(f"处理菜单点击出错: {str(e)}")
            return "处理出错，请稍后重试"

# 创建服务实例
stock_service = StockService()

@app.route('/wx', methods=['GET', 'POST'])
def handle_request():
    """处理微信请求"""
    try:
        if request.method == 'GET':
            # 处理服务器认证
            signature = request.args.get('signature', '')
            timestamp = request.args.get('timestamp', '')
            nonce = request.args.get('nonce', '')
            echostr = request.args.get('echostr', '')
            
            if check_signature(signature, timestamp, nonce):
                return echostr
            return 'Invalid signature'
            
        elif request.method == 'POST':
            # 处理消息
            xml_str = request.data
            logger.info(f"收到微信消息: {xml_str}")
            msg_dict = parse_xml(xml_str)
            
            if msg_dict.get('MsgType') == 'event' and msg_dict.get('Event') == 'CLICK':
                # 处理菜单点击事件
                event_key = msg_dict.get('EventKey')
                response = stock_service.handle_menu_click(msg_dict.get('FromUserName'), event_key)
                return format_reply(msg_dict, response)
            
            elif msg_dict.get('MsgType') == 'text':
                content = msg_dict.get('Content', '').strip()
                user_id = msg_dict.get('FromUserName')
                
                logger.info(f"用户 {user_id} 发送消息: {content}")
                
                # 解析命令
                parts = content.split()
                if parts and parts[0].lower() in stock_service.commands:
                    # 如果是已知命令，执行对应的处理函数
                    command = parts[0].lower()
                    args = parts[1:] if len(parts) > 1 else []
                    handler = stock_service.commands[command]
                    response = handler(user_id, args)
                else:
                    # 如果不是已知命令，显示帮助信息
                    response = stock_service.show_help(user_id)
                
                # 返回响应
                reply = format_reply(msg_dict, response)
                logger.info(f"返回消息: {reply}")
                return reply
                
            return format_reply(msg_dict, '目前只支持文本消息')
            
    except Exception as e:
        logger.error(f"处理请求出错: {str(e)}")
        return format_reply({'FromUserName': '', 'ToUserName': ''}, '服务器处理出错，请稍后重试')

def check_signature(signature, timestamp, nonce):
    """检查签名"""
    # 实现签名验证逻辑
    return True

def parse_xml(xml_str):
    """解析XML"""
    try:
        root = ET.fromstring(xml_str)
        msg = {}
        for child in root:
            msg[child.tag] = child.text
        return msg
    except Exception as e:
        logger.error(f"解析XML出错: {str(e)}")
        return {}

def format_reply(msg, content):
    """格式化回复消息"""
    return f"""<xml>
    <ToUserName><![CDATA[{msg.get('FromUserName', '')}]]></ToUserName>
    <FromUserName><![CDATA[{msg.get('ToUserName', '')}]]></FromUserName>
    <CreateTime>{int(datetime.now().timestamp())}</CreateTime>
    <MsgType><![CDATA[text]]></MsgType>
    <Content><![CDATA[{content}]]></Content>
    </xml>"""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True) 