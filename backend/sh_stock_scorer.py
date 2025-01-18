import pandas as pd
from sqlalchemy import text
import logging
from datetime import datetime, timedelta
import argparse
from sh_stock_db import get_db_engine

logger = logging.getLogger(__name__)

class BaseScorer:
    """评分策略基类"""
    
    def __init__(self, engine):
        self.engine = engine
    
    def calculate_scores(self, date_str=None, top_n=10):
        """计算评分"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            
        try:
            df = pd.read_sql(text(self.get_score_query(date_str)), 
                           self.engine, 
                           params={'score_date': date_str})
            
            # 打印评分结果
            print(f"\n计算 {date_str} 的{self.__class__.__doc__.split()[0]}:")
            print(f"共计算 {len(df)} 只股票的评分")
            
            # 打印指标说明
            self.print_metric_description()
            
            # 打印前N名
            print(f"\n评分前{top_n}名股票:")
            top_n_df = df.head(top_n)
            for _, row in top_n_df.iterrows():
                score_details = []
                for col in df.columns:
                    if col not in ['stock_code', 'stock_name', 'total_score']:
                        if isinstance(row[col], (int, float)):
                            score_details.append(f"{col}={row[col]:.2f}")
                        else:
                            score_details.append(f"{col}={row[col]}")
                
                print(
                    f"{row['stock_code']} {row['stock_name']}: "
                    f"总分={float(row['total_score']):.2f} "
                    f"({', '.join(score_details)})"
                )
            
            return df
            
        except Exception as e:
            logger.error(f"计算评分时出错: {str(e)}")
            return None

class ValueScorer(BaseScorer):
    """价值型投资策略"""
    
    def get_score_query(self, score_date):
        return """
        WITH industry_pe AS (
            -- 计算行业平均PE
            SELECT s.industry, AVG(f.pe_ratio) as avg_pe
            FROM stocks s
            JOIN fundamental_metrics f ON s.stock_code = f.stock_code
            WHERE f.date = :score_date
            GROUP BY s.industry
        )
        SELECT 
            s.stock_code,
            s.stock_name,
            s.industry,
            f.pe_ratio,
            f.pb_ratio,
            f.roe,
            f.gross_margin,
            i.industry_rank,
            -- 评分计算
            ROUND(
                CASE 
                    WHEN f.pe_ratio < ip.avg_pe * 0.8 THEN 30 
                    WHEN f.pe_ratio < ip.avg_pe THEN 20
                    ELSE 10 
                END +
                CASE 
                    WHEN f.pb_ratio < 3 THEN 20
                    WHEN f.pb_ratio < 5 THEN 10
                    ELSE 0 
                END +
                CASE 
                    WHEN f.roe > 15 THEN 30
                    WHEN f.roe > 10 THEN 20
                    ELSE 10 
                END +
                CASE 
                    WHEN f.gross_margin > 40 THEN 10
                    WHEN f.gross_margin > 30 THEN 5
                    ELSE 0 
                END +
                CASE 
                    WHEN i.industry_rank <= 5 THEN 10
                    WHEN i.industry_rank <= 10 THEN 5
                    ELSE 0 
                END
            , 2) as total_score
        FROM stocks s
        JOIN fundamental_metrics f ON s.stock_code = f.stock_code
        JOIN industry_metrics i ON s.stock_code = i.stock_code
        JOIN industry_pe ip ON s.industry = ip.industry
        WHERE f.date = :score_date
          AND i.date = :score_date
        ORDER BY total_score DESC
        """
    
    def print_metric_description(self):
        print("\n指标说明:")
        print("- pe_ratio: 市盈率，反映股票估值水平")
        print("- pb_ratio: 市净率，反映公司账面价值")
        print("- roe: 净资产收益率，反映公司盈利能力")
        print("- gross_margin: 毛利率，反映产品盈利能力")
        print("- industry_rank: 行业排名")
        print("\n评分标准:")
        print("1. 市盈率(30分): 低于行业均值20%得30分，低于均值得20分，其他得10分")
        print("2. 市净率(20分): <3倍得20分，<5倍得10分")
        print("3. ROE(30分): >15%得30分，>10%得20分，其他得10分")
        print("4. 毛利率(10分): >40%得10分，>30%得5分")
        print("5. 行业排名(10分): 前5名得10分，前10名得5分")

class GrowthScorer(BaseScorer):
    """成长型投资策略"""
    
    def get_score_query(self, score_date):
        return """
        SELECT 
            s.stock_code,
            s.stock_name,
            f.revenue_growth,
            f.earnings_growth,
            t.current_price,
            t.ma_200,
            fh.current_ratio,
            -- 评分计算
            ROUND(
                CASE 
                    WHEN f.revenue_growth > 20 THEN 30
                    WHEN f.revenue_growth > 15 THEN 20
                    ELSE 10 
                END +
                CASE 
                    WHEN f.earnings_growth > 25 THEN 30
                    WHEN f.earnings_growth > 20 THEN 20
                    ELSE 10 
                END +
                CASE 
                    WHEN t.current_price > t.ma_200 THEN 20
                    ELSE 0 
                END +
                CASE 
                    WHEN fh.current_ratio >= 1.5 THEN 20
                    WHEN fh.current_ratio >= 1.2 THEN 10
                    ELSE 0 
                END
            , 2) as total_score
        FROM stocks s
        JOIN fundamental_metrics f ON s.stock_code = f.stock_code
        JOIN technical_metrics t ON s.stock_code = t.stock_code
        JOIN financial_health fh ON s.stock_code = fh.stock_code
        WHERE f.date = :score_date
          AND t.date = :score_date
          AND fh.report_date = (
              SELECT MAX(report_date) 
              FROM financial_health 
              WHERE report_date <= :score_date
          )
        ORDER BY total_score DESC
        """
    
    def print_metric_description(self):
        """打印指标说明"""
        print("\n指标说明:")
        print("- revenue_growth: 营业收入增长率，反映公司业务规模扩张速度")
        print("- earnings_growth: 净利润增长率，反映公司盈利能力提升情况")
        print("- current_price: 当前股价")
        print("- ma_200: 200日均线，反映中长期趋势")
        print("- current_ratio: 流动比率(流动资产/流动负债)，反映短期偿债能力")
        print("\n评分标准:")
        print("1. 营收增长(30分): >20%得30分，>15%得20分，其他得10分")
        print("2. 利润增长(30分): >25%得30分，>20%得20分，其他得10分")
        print("3. 价格趋势(20分): 股价>200日均线得20分")
        print("4. 流动比率(20分): >=1.5得20分，>=1.2得10分")

class IncomeScorer(BaseScorer):
    """收益型投资策略"""
    
    def get_score_query(self, score_date):
        return """
        SELECT 
            s.stock_code,
            s.stock_name,
            f.dividend_yield,
            t.beta,
            fh.quick_ratio,
            -- 评分计算
            ROUND(
                CASE 
                    WHEN f.dividend_yield > 5 THEN 40
                    WHEN f.dividend_yield > 3 THEN 30
                    WHEN f.dividend_yield > 2 THEN 20
                    ELSE 0 
                END +
                CASE 
                    WHEN t.beta < 0.6 THEN 30
                    WHEN t.beta < 0.8 THEN 20
                    WHEN t.beta < 1.0 THEN 10
                    ELSE 0 
                END +
                CASE 
                    WHEN fh.quick_ratio > 1.5 THEN 30
                    WHEN fh.quick_ratio > 1.0 THEN 20
                    ELSE 0 
                END
            , 2) as total_score
        FROM stocks s
        JOIN fundamental_metrics f ON s.stock_code = f.stock_code
        JOIN technical_metrics t ON s.stock_code = t.stock_code
        JOIN financial_health fh ON s.stock_code = fh.stock_code
        WHERE f.date = :score_date
          AND t.date = :score_date
          AND fh.report_date = (
              SELECT MAX(report_date) 
              FROM financial_health 
              WHERE report_date <= :score_date
          )
        ORDER BY total_score DESC
        """
    
    def print_metric_description(self):
        print("\n指标说明:")
        print("- dividend_yield: 股息率，反映现金分红收益")
        print("- beta: 贝塔系数，反映股价波动风险")
        print("- quick_ratio: 速动比率，反映即时偿债能力")
        print("\n评分标准:")
        print("1. 股息率(40分): >5%得40分，>3%得30分，>2%得20分")
        print("2. 贝塔系数(30分): <0.6得30分，<0.8得20分，<1得10分")
        print("3. 速动比率(30分): >1.5得30分，>1.2得20分，>1得10分")

class TrendScorer(BaseScorer):
    """趋势交易策略"""
    
    def get_score_query(self, score_date):
        return """
        WITH rsi_calc AS (
            SELECT stock_code,
                   100 - 100 / (1 + AVG(gain) / NULLIF(AVG(loss), 0)) as rsi
            FROM (
                SELECT stock_code,
                       GREATEST(current_price - LAG(current_price) OVER (PARTITION BY stock_code ORDER BY date), 0) AS gain,
                       GREATEST(LAG(current_price) OVER (PARTITION BY stock_code ORDER BY date) - current_price, 0) AS loss
                FROM technical_metrics
                WHERE date >= :score_date - INTERVAL 14 DAY
            ) price_changes
            GROUP BY stock_code
        )
        SELECT 
            s.stock_code,
            s.stock_name,
            t.current_price,
            t.high_52week,
            t.volume,
            t.avg_volume_10d,
            rc.rsi,
            -- 评分计算
            ROUND(
                CASE 
                    WHEN t.current_price > t.high_52week * 0.95 THEN 30
                    WHEN t.current_price > t.high_52week * 0.90 THEN 20
                    ELSE 0 
                END +
                CASE 
                    WHEN t.volume > t.avg_volume_10d * 2 THEN 30
                    WHEN t.volume > t.avg_volume_10d * 1.5 THEN 20
                    ELSE 0 
                END +
                CASE 
                    WHEN rc.rsi BETWEEN 50 AND 80 THEN 40
                    WHEN rc.rsi BETWEEN 40 AND 90 THEN 20
                    ELSE 0 
                END
            , 2) as total_score
        FROM stocks s
        JOIN technical_metrics t ON s.stock_code = t.stock_code
        JOIN rsi_calc rc ON s.stock_code = rc.stock_code
        WHERE t.date = :score_date
        ORDER BY total_score DESC
        """
    
    def print_metric_description(self):
        print("\n指标说明:")
        print("- current_price: 当前股价")
        print("- high_52week: 52周最高价，反映年度价格区间")
        print("- volume: 当日成交量")
        print("- avg_volume_10d: 10日平均成交量")
        print("- rsi: 相对强弱指数，反映股价超买超卖情况")
        print("\n评分标准:")
        print("1. 价格位置(30分): 接近52周高点95%得30分，接近90%得20分")
        print("2. 成交量(30分): 大于10日均量2倍得30分，大于1.5倍得20分")
        print("3. RSI指标(40分): 50-80区间得40分，40-90区间得20分")

class ReverseScorer(BaseScorer):
    """反向投资策略"""
    
    def get_score_query(self, score_date):
        return """
        SELECT 
            s.stock_code,
            s.stock_name,
            t.current_price,
            t.low_52week,
            f.roe,
            f.gross_margin,
            im.insider_holding,
            -- 评分计算
            ROUND(
                CASE 
                    WHEN t.current_price < t.low_52week * 1.05 THEN 40
                    WHEN t.current_price < t.low_52week * 1.10 THEN 30
                    WHEN t.current_price < t.low_52week * 1.15 THEN 20
                    ELSE 0 
                END +
                CASE 
                    WHEN f.roe > 15 THEN 30
                    WHEN f.roe > 10 THEN 20
                    ELSE 0 
                END +
                CASE 
                    WHEN f.gross_margin > 40 THEN 20
                    WHEN f.gross_margin > 30 THEN 10
                    ELSE 0 
                END +
                CASE 
                    WHEN im.insider_holding > 50 THEN 10
                    WHEN im.insider_holding > 30 THEN 5
                    ELSE 0 
                END
            , 2) as total_score
        FROM stocks s
        JOIN technical_metrics t ON s.stock_code = t.stock_code
        JOIN fundamental_metrics f ON s.stock_code = f.stock_code
        JOIN investor_metrics im ON s.stock_code = im.stock_code
        WHERE t.date = :score_date
          AND f.date = :score_date
          AND im.date = :score_date
        ORDER BY total_score DESC
        """
    
    def print_metric_description(self):
        print("\n指标说明:")
        print("- current_price: 当前股价")
        print("- low_52week: 52周最低价，反映年度价格区间")
        print("- roe: 净资产收益率，反映公司盈利能力")
        print("- gross_margin: 毛利率，反映产品盈利能力")
        print("- insider_holding: 内部持股比例，反映管理层信心")
        print("\n评分标准:")
        print("1. 价格位置(40分): 接近52周低点5%内得40分，10%内得30分，15%内得20分")
        print("2. ROE指标(30分): >15%得30分，>10%得20分")
        print("3. 毛利率(20分): >40%得20分，>30%得10分")
        print("4. 内部持股(10分): >50%得10分，>30%得5分")

class RTPVScorer(BaseScorer):
    """RTPV综合评分策略"""
    
    def get_score_query(self, score_date, period_days=30):
        return """
        WITH price_changes AS (
            SELECT stock_code, date,
                   GREATEST(current_price - LAG(current_price) OVER (PARTITION BY stock_code ORDER BY date), 0) AS gain,
                   GREATEST(LAG(current_price) OVER (PARTITION BY stock_code ORDER BY date) - current_price, 0) AS loss
            FROM technical_metrics
            WHERE date >= :score_date - INTERVAL :period_days DAY
        ),
        fundamental_score AS (
            SELECT stock_code, roe
            FROM fundamental_metrics
            WHERE date = (SELECT MAX(date) FROM fundamental_metrics WHERE date <= :score_date)
        ),
        technical_score AS (
            SELECT pc.stock_code,
                   100 - 100 / (1 + COALESCE(AVG(pc.gain), 0) / NULLIF(COALESCE(AVG(pc.loss), 0), 0)) AS rsi,
                   (MAX(tm.current_price) - MIN(tm.current_price)) / NULLIF(MIN(tm.current_price), 0) * 100 AS price_change_percent,
                   COALESCE(AVG(tm.volume), 0) AS avg_volume_30d
            FROM price_changes pc
            JOIN technical_metrics tm ON pc.stock_code = tm.stock_code AND pc.date = tm.date
            WHERE tm.date >= :score_date - INTERVAL :period_days DAY
            GROUP BY pc.stock_code
        )
        SELECT 
            s.stock_code, 
            s.stock_name,
            fs.roe AS roe_score,
            ts.rsi AS rsi_score,
            ts.price_change_percent AS price_change_score,
            (COALESCE(tm.volume, 0) / NULLIF(COALESCE(ts.avg_volume_30d, 1), 0)) AS volume_ratio,
            ROUND(0.3 * COALESCE(fs.roe, 0) +
                  0.3 * COALESCE(ts.rsi, 0) +
                  0.3 * COALESCE(ts.price_change_percent, 0) +
                  0.1 * (COALESCE(tm.volume, 0) / NULLIF(COALESCE(ts.avg_volume_30d, 1), 0)), 2) AS total_score
        FROM stocks s
        LEFT JOIN fundamental_score fs ON s.stock_code = fs.stock_code
        LEFT JOIN technical_score ts ON s.stock_code = ts.stock_code
        LEFT JOIN technical_metrics tm ON s.stock_code = tm.stock_code AND tm.date = :score_date
        ORDER BY total_score DESC
        """
    
    def calculate_scores(self, date_str=None, period_days=30, top_n=10):
        """RTPV策略特殊处理，需要period_days参数"""
        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')
            
        try:
            df = pd.read_sql(text(self.get_score_query(date_str, period_days)), 
                           self.engine, 
                           params={'score_date': date_str, 'period_days': period_days})
            
            # 打印评分结果
            print(f"\n计算 {date_str} 的RTPV评分:")
            print(f"计算周期: {period_days}天")
            print(f"共计算 {len(df)} 只股票的评分")
            
            # 打印指标说明
            self.print_metric_description()
            
            # 打印前N名
            print(f"\n评分前{top_n}名股票:")
            top_n_df = df.head(top_n)
            for _, row in top_n_df.iterrows():
                print(
                    f"{row['stock_code']} {row['stock_name']}: "
                    f"总分={float(row['total_score']):.2f} "
                    f"(ROE={float(row['roe_score']):.2f}, "
                    f"RSI={float(row['rsi_score']):.2f}, "
                    f"价格变动={float(row['price_change_score']):.2f}%, "
                    f"成交量比={float(row['volume_ratio']):.2f})"
                )
            
            return df
            
        except Exception as e:
            logger.error(f"计算RTPV评分时出错: {str(e)}")
            return None
    
    def print_metric_description(self):
        """打印指标说明"""
        print("\n指标说明:")
        print("- roe: 净资产收益率，反映公司盈利能力")
        print("- rsi: 相对强弱指数，反映股价波动风险")
        print("- 价格变动: 价格变动百分比，反映股价波动情况")
        print("- 成交量比: 成交量比，反映成交量与平均成交量的关系")
        print("\n评分标准:")
        print("1. ROE(30分): >0%得30分，>0%得20分，其他得10分")
        print("2. RSI(30分): 50-80得40分，40-90得20分，其他得0分")
        print("3. 价格变动(30分): 价格变动百分比>0%得30分，>0%得20分，其他得10分")
        print("4. 成交量比(10分): >1得10分，>0.5得5分")

def main():
    parser = argparse.ArgumentParser(description='股票评分程序')
    parser.add_argument('--strategy', default='rtpv', 
                       choices=['rtpv', 'value', 'growth', 'income', 'trend', 'reverse'], 
                       help='评分策略: rtpv-RTPV综合策略, value-价值型策略, growth-成长型策略, '
                            'income-收益型策略, trend-趋势交易策略, reverse-反向投资策略')
    parser.add_argument('--date', help='指定日期 (YYYY-MM-DD)')
    parser.add_argument('--period', type=int, default=30, help='计算周期（天数）')
    parser.add_argument('--top', type=int, default=10, help='显示前N名股票')
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    engine = get_db_engine()
    
    strategies = {
        'rtpv': RTPVScorer,
        'value': ValueScorer,
        'growth': GrowthScorer,
        'income': IncomeScorer,
        'trend': TrendScorer,
        'reverse': ReverseScorer
    }
    
    if args.strategy in strategies:
        scorer = strategies[args.strategy](engine)
        if args.strategy == 'rtpv':
            scorer.calculate_scores(args.date, args.period, args.top)
        else:
            scorer.calculate_scores(args.date, args.top)
    else:
        logger.error(f"未知的评分策略: {args.strategy}")

if __name__ == "__main__":
    main() 