from urllib.parse import quote_plus

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'stock_app',  # 应用程序用户
    'password': quote_plus('xxxxxx'),  # URL编码密码
    'database': 'stock_analysis'
}

# 只读配置（用于数据分析）
DB_CONFIG_READER = {
    'host': 'localhost',
    'user': 'stock_reader',
    'password': quote_plus('xxxxxx'),
    'database': 'stock_analysis'
}

# 管理员配置（用于维护）
DB_CONFIG_ADMIN = {
    'host': 'localhost',
    'user': 'stock_admin',
    'password': quote_plus('xxxxxxxx'),
    'database': 'stock_analysis'
}