import os
import json
import pandas as pd
from datetime import datetime, date
import logging
import argparse

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        return super().default(obj)

def process_stock_metrics(info, stock_code, trade_date):
    """处理股票各类指标"""
    # 将日期转换为字符串格式
    date_str = trade_date.strftime('%Y-%m-%d')
    
    return {
        # 基本面指标
        'fundamental': {
            'stock_code': stock_code,
            'date': date_str,  # 使用字符串格式的日期
            'pe_ratio': info.get('forwardPE'),
            'pb_ratio': info.get('priceToBook'),
            'roe': info.get('returnOnEquity'),
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'gross_margin': info.get('grossMargins'),
            'operating_margin': info.get('operatingMargins'),
            'dividend_yield': info.get('fiveYearAvgDividendYield'),
        },
        
        # 技术面指标
        'technical': {
            'stock_code': stock_code,
            'date': date_str,  # 使用字符串格式的日期
            'current_price': info.get('currentPrice'),
            'high_52week': info.get('fiftyTwoWeekHigh'),
            'low_52week': info.get('fiftyTwoWeekLow'),
            'volume': info.get('volume'),
            'avg_volume': info.get('averageVolume'),
            'avg_volume_10d': info.get('averageVolume10days'),
            'ma_200': info.get('twoHundredDayAverage'),
            'beta': info.get('beta'),
        },
        
        # 财务健康指标
        'financial': {
            'stock_code': stock_code,
            'report_date': date_str,  # 使用字符串格式的日期
            # 偿债能力指标
            'quick_ratio': info.get('quickRatio'),
            'current_ratio': info.get('currentRatio'),
            'cash_ratio': info.get('cashRatio'),
            'debt_to_equity': info.get('debtToEquity'),
            'interest_coverage': info.get('interestCoverage'),
            
            # 现金流指标
            'operating_cash_flow': info.get('operatingCashflow'),
            'investing_cash_flow': info.get('investingCashflow'),
            'financing_cash_flow': info.get('financingCashflow'),
            'free_cash_flow': info.get('freeCashflow'),
            'cash_flow_coverage': info.get('cashFlowCoverage')
        },
        
        # 行业指标
        'industry': {
            'stock_code': stock_code,
            'date': date_str,  # 使用字符串格式的日期
            'profit_margin': info.get('profitMargins'),
            'price_to_sales': info.get('priceToSalesTrailing12Months'),
            'industry_rank': info.get('industryRank')
        },
        
        # 投资者行为指标
        'investor': {
            'stock_code': stock_code,
            'date': date_str,  # 使用字符串格式的日期
            'insider_holding': info.get('heldPercentInsiders'),
            'institution_holding': info.get('heldPercentInstitutions')
        }
    }

def analyze_stock_info(full_history=False):
    """分析股票信息并生成分析报告"""
    start_time = datetime.now()
    
    # 检查原始数据目录
    stock_info_dir = 'stock_info'
    if not os.path.exists(stock_info_dir):
        logger.error("未找到 stock_info 目录，请先运行 sh_stock_downloader.py")
        return
    
    # 创建分析结果目录
    analysis_dir = 'stock_analysis'
    if not os.path.exists(analysis_dir):
        os.makedirs(analysis_dir)
    
    # 获取日期目录列表
    date_dirs = []
    for d in os.listdir(stock_info_dir):
        try:
            if '-' in d:  # YYYY-MM-DD 格式
                parsed_date = datetime.strptime(d, '%Y-%m-%d')
                date_dirs.append((d, parsed_date))
            elif len(d) == 8 and d.isdigit():  # YYYYMMDD 格式
                parsed_date = datetime.strptime(d, '%Y%m%d')
                date_dirs.append((d, parsed_date))
        except ValueError:
            continue

    if not date_dirs:
        logger.error("未找到任何日期目录")
        return
    
    # 根据参数决定处理哪些日期
    date_dirs.sort(key=lambda x: x[1])
    dates_to_process = [d[0] for d in date_dirs] if full_history else [date_dirs[-1][0]]
    
    # 处理每个日期的数据
    for date_dir in dates_to_process:
        try:
            date_path = os.path.join(stock_info_dir, date_dir)
            trade_date = datetime.strptime(date_dir.replace('-', ''), '%Y%m%d').date()
            
            logger.info(f"\n处理 {trade_date} 的数据...")
            
            # 创建分析结果目录
            analysis_date_dir = os.path.join(analysis_dir, date_dir)
            if not os.path.exists(analysis_date_dir):
                os.makedirs(analysis_date_dir)

            # 遍历板块目录
            for sector in os.listdir(date_path):
                sector_path = os.path.join(date_path, sector)
                if os.path.isdir(sector_path):
                    analysis_sector_dir = os.path.join(analysis_date_dir, sector)
                    if not os.path.exists(analysis_sector_dir):
                        os.makedirs(analysis_sector_dir)
                    
                    logger.info(f"\n分析 {sector} 板块...")
                    sector_data = []
                    
                    # 处理只股票
                    for file in os.listdir(sector_path):
                        if file.endswith('_info.json'):
                            try:
                                with open(os.path.join(sector_path, file), 'r', encoding='utf-8') as f:
                                    info = json.load(f)
                                    metrics = process_stock_metrics(info, info['stock_code'], trade_date)
                                    
                                    # 保存处理后的指标
                                    for metric_type, data in metrics.items():
                                        metric_dir = os.path.join(analysis_sector_dir, metric_type)
                                        if not os.path.exists(metric_dir):
                                            os.makedirs(metric_dir)
                                        
                                        output_file = os.path.join(metric_dir, f"{info['stock_code']}_{info['stock_name']}_{metric_type}.json")
                                        with open(output_file, 'w', encoding='utf-8') as f:
                                            json.dump(data, f, ensure_ascii=False, indent=4, cls=DateEncoder)
                                    
                                    # 收集板块分析数据
                                    sector_data.append({
                                        'stock_code': info['stock_code'],
                                        'stock_name': info['stock_name'],
                                        'pe_ratio': metrics['fundamental']['pe_ratio'],
                                        'pb_ratio': metrics['fundamental']['pb_ratio'],
                                        'current_price': metrics['technical']['current_price'],
                                        'volume': metrics['technical']['volume']
                                    })
                                    
                            except Exception as e:
                                logger.error(f"处理文件 {file} 时出错: {str(e)}")
                                continue
                    
                    # 生成板块分析报告
                    if sector_data:
                        df = pd.DataFrame(sector_data)
                        
                        # 保存汇总数据
                        summary_file = os.path.join(analysis_sector_dir, f'{sector}_summary.csv')
                        df.to_csv(summary_file, index=False, encoding='utf-8-sig')
                        
                        # 生成统计报告
                        stats_file = os.path.join(analysis_sector_dir, f'{sector}_stats.txt')
                        with open(stats_file, 'w', encoding='utf-8') as f:
                            f.write(f"{sector}板块统计报告 ({trade_date})\n")
                            f.write(f"股票数量: {len(df)}\n")
                            f.write(f"平均市盈率: {df['pe_ratio'].mean():.2f}\n")
                            f.write(f"平均市净率: {df['pb_ratio'].mean():.2f}\n")
                            f.write(f"平均成交量: {df['volume'].mean():.0f}\n")

        except Exception as e:
            logger.error(f"处理日期目录 {date_dir} 时出错: {str(e)}")
            continue

    end_time = datetime.now()
    logger.info(f"\n分析完成! 总耗时: {end_time - start_time}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='股票数据分析程序')
    parser.add_argument('--full', action='store_true', 
                      help='处理所有历史数据（默认只处理最新日期）')
    args = parser.parse_args()

    logger.info("开始分析股票信息...")
    analyze_stock_info(full_history=args.full) 