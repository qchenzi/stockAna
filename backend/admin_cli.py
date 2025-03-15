import os
import sys
import subprocess
from datetime import datetime
import inquirer

class AdminCLI:
    def __init__(self):
        self.clear_screen()
        
    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def run_command(self, command):
        """执行命令并等待用户确认"""
        try:
            subprocess.run(command, shell=True, check=True)
            input("\n按回车键继续...")
        except subprocess.CalledProcessError as e:
            print(f"\n执行出错: {str(e)}")
            input("\n按回车键继续...")
    
    def main_menu(self):
        """管理员主菜单"""
        while True:
            self.clear_screen()
            print("=== 股票数据管理系统(管理员) ===\n")
            
            questions = [
                inquirer.List('choice',
                    message="请选择操作",
                    choices=[
                        ('股票基本面数据管理', 'fundamental'),
                        ('历史交易数据管理', 'historical'),
                        ('退出程序', 'exit')
                    ]
                )
            ]
            
            answer = inquirer.prompt(questions)
            
            if answer['choice'] == 'fundamental':
                self.fundamental_menu()
            elif answer['choice'] == 'historical':
                self.historical_menu()
            else:
                sys.exit(0)

    def fundamental_menu(self):
        """股票基本面数据管理菜单"""
        while True:
            self.clear_screen()
            print("=== 股票基本面数据管理 ===\n")
            
            questions = [
                inquirer.List('choice',
                    message="请选择操作",
                    choices=[
                        ('数据采集', 'collect'),
                        ('数据分析', 'analyze'),
                        ('数据入库', 'import'),
                        ('数据清理', 'clean'),
                        ('系统维护', 'maintain'),
                        ('返回上级菜单', 'back')
                    ]
                )
            ]
            
            answer = inquirer.prompt(questions)
            
            if answer['choice'] == 'collect':
                self.collect_menu()
            elif answer['choice'] == 'analyze':
                self.analyze_menu()
            elif answer['choice'] == 'import':
                self.import_menu()
            elif answer['choice'] == 'clean':
                self.clean_menu()
            elif answer['choice'] == 'maintain':
                self.maintain_menu()
            else:
                break

    def historical_menu(self):
        """历史交易数据管理菜单"""
        while True:
            self.clear_screen()
            print("=== 历史交易数据管理 ===\n")
            
            questions = [
                inquirer.List('choice',
                    message="请选择操作",
                    choices=[
                        ('数据下载', 'download'),
                        ('数据入库', 'database'),
                        ('筹码分析', 'chip'),
                        ('技术评分', 'technical'),
                        ('返回上级菜单', 'back')
                    ]
                )
            ]
            
            answer = inquirer.prompt(questions)
            
            if answer['choice'] == 'download':
                self.historical_download_menu()
            elif answer['choice'] == 'database':
                self.historical_database_menu()
            elif answer['choice'] == 'chip':
                self.historical_chip_menu()
            elif answer['choice'] == 'technical':
                self.historical_technical_menu()
            else:
                break

    def historical_download_menu(self):
        """历史数据下载菜单"""
        self.clear_screen()
        print("=== 历史数据下载 ===\n")
        
        questions = [
            inquirer.List('mode',
                message="请选择下载模式",
                choices=[
                    ('下载指定日期数据', 'specific'),
                    ('下载最新数据', 'latest'),
                    ('返回上级菜单', 'back')
                ]
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if answer['mode'] == 'specific':
            start_date = inquirer.text(message="请输入开始日期(YYYY-MM-DD)")
            end_date = inquirer.text(message="请输入结束日期(YYYY-MM-DD)")
            stock_list = inquirer.text(message="请输入股票列表文件路径", default="stock_list.csv")
            output_dir = inquirer.text(
                message="请输入输出目录",
                default=f"stock_history/data/custom_period/{datetime.now().strftime('%Y-%m-%d')}"
            )
            workers = inquirer.text(message="请输入并发数(默认3)", default="3")
            
            if start_date.strip() and end_date.strip():
                self.run_command(
                    f'python3 -m stock_history.downloader.ak_downloader '
                    f'-o {output_dir} -s {stock_list} '
                    f'--start-date {start_date} --end-date {end_date} '
                    f'--workers {workers}'
                )
        elif answer['mode'] == 'latest':
            stock_list = inquirer.text(message="请输入股票列表文件路径", default="stock_list.csv")
            today = datetime.now().strftime('%Y-%m-%d')
            output_dir = inquirer.text(
                message="请输入输出目录",
                default=f"stock_history/data/latest/{today}"
            )
            workers = inquirer.text(message="请输入并发数(默认3)", default="3")
            
            self.run_command(
                f'python3 -m stock_history.downloader.ak_downloader '
                f'-o {output_dir} -s {stock_list} '
                f'--workers {workers}'
            )

    def historical_database_menu(self):
        """历史数据库操作菜单"""
        self.clear_screen()
        print("=== 历史数据库操作 ===\n")
        
        questions = [
            inquirer.List('action',
                message="请选择操作",
                choices=[
                    ('导入数据', 'import'),
                    ('删除数据', 'delete'),
                    ('返回上级菜单', 'back')
                ]
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if answer['action'] == 'import':
            data_dir = inquirer.text(
                message="请输入数据目录路径",
                default="stock_history/data/latest"
            )
            mode = inquirer.list_input(
                message="请选择导入模式",
                choices=['all', 'date_range']
            )
            workers = inquirer.text(message="请输入并发数(默认5)", default="5")
            
            if mode == 'date_range':
                start_date = inquirer.text(message="请输入开始日期(YYYY-MM-DD)")
                end_date = inquirer.text(message="请输入结束日期(YYYY-MM-DD)")
                if start_date.strip() and end_date.strip():
                    self.run_command(
                        f'python3 -m stock_history.db.history_db import '
                        f'--data-dir {data_dir} '
                        f'--mode {mode} '
                        f'--start-date {start_date} '
                        f'--end-date {end_date} '
                        f'--workers {workers}'
                    )
            else:
                self.run_command(
                    f'python3 -m stock_history.db.history_db import '
                    f'--data-dir {data_dir} '
                    f'--mode {mode} '
                    f'--workers {workers}'
                )
                
        elif answer['action'] == 'delete':
            stock_code = inquirer.text(message="请输入股票代码(可选)")
            start_date = inquirer.text(message="请输入开始日期(YYYY-MM-DD，必填)")
            end_date = inquirer.text(message="请输入结束日期(YYYY-MM-DD，必填)")
            
            if start_date.strip() and end_date.strip():
                cmd = (f'python3 -m stock_history.db.history_db delete '
                      f'--start-date {start_date} --end-date {end_date}')
                if stock_code.strip():
                    cmd += f' --stock-code {stock_code}'
                
                confirm = inquirer.confirm(
                    message=f"确定要删除这些数据吗？此操作不可恢复！",
                    default=False
                )
                if confirm:
                    self.run_command(cmd)

    def historical_chip_menu(self):
        """筹码分析菜单"""
        self.clear_screen()
        print("=== 筹码分析 ===\n")
        
        questions = [
            inquirer.List('action',
                message="请选择操作",
                choices=[
                    ('更新今日筹码分析', 'update'),
                    ('返回上级菜单', 'back')
                ]
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if answer['action'] == 'update':
            self.run_command('python3 scripts/stock_chip_analyzer.py')

    def historical_technical_menu(self):
        """技术评分菜单"""
        self.clear_screen()
        print("=== 技术评分 ===\n")
        
        questions = [
            inquirer.List('action',
                message="请选择操作",
                choices=[
                    ('更新今日技术评分', 'update'),
                    ('返回上级菜单', 'back')
                ]
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if answer['action'] == 'update':
            self.run_command('python3 scripts/stock_technical_scorer.py')

    def collect_menu(self):
        """数据采集菜单"""
        self.clear_screen()
        print("=== 数据采集 ===\n")
        
        questions = [
            inquirer.List('step',
                message="请选择采集步骤",
                choices=[
                    ('获取股票列表', 'list'),
                    ('下载股票数据（yfinance需要科学上网）', 'download'),
                    ('返回上级菜单', 'back')
                ]
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if answer['step'] == 'list':
            self.run_command('python3 scripts/stock_code_scraper.py')
        elif answer['step'] == 'download':
            workers = inquirer.text(message="请输入并发数(默认10)")
            workers = workers.strip() or "10"
            self.run_command(f'python3 scripts/stock_downloader.py --workers {workers}')
        elif answer['step'] == 'all':
            workers = inquirer.text(message="请输入并发数(默认10)")
            workers = workers.strip() or "10"
            self.run_command('python3 scripts/stock_code_scraper.py')
            self.run_command(f'python3 scripts/stock_downloader.py --workers {workers}')
    
    def analyze_menu(self):
        """数据分析菜单"""
        self.clear_screen()
        print("=== 数据分析 ===\n")
        
        questions = [
            inquirer.List('mode',
                message="请选择分析模式",
                choices=[
                    ('处理最新数据', 'latest'),
                    ('处理历史数据', 'history'),
                    ('分析指定日期', 'specific'),
                    ('返回上级菜单', 'back')
                ]
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if answer['mode'] == 'latest':
            self.run_command('python3 scripts/stock_analyzer.py')
        elif answer['mode'] == 'history':
            self.run_command('python3 scripts/stock_analyzer.py --full')
        elif answer['mode'] == 'specific':
            date = inquirer.text(message="请输入日期(YYYY-MM-DD)")
            if date.strip():
                self.run_command(f'python3 scripts/stock_analyzer.py --date {date}')
    
    def import_menu(self):
        """数据入库菜单"""
        self.clear_screen()
        print("=== 数据入库 ===\n")
        
        questions = [
            inquirer.List('mode',
                message="请选择入库模式",
                choices=[
                    ('导入最新数据', 'latest'),
                    ('导入历史数据', 'history'),
                    ('导入指定日期', 'specific'),
                    ('返回上级菜单', 'back')
                ]
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if answer['mode'] == 'latest':
            workers = inquirer.text(message="请输入并发数(默认20)")
            workers = workers.strip() or "20"
            self.run_command(f'python3 scripts/stock_db.py --workers {workers}')
        elif answer['mode'] == 'history':
            workers = inquirer.text(message="请输入并发数(默认20)")
            workers = workers.strip() or "20"
            self.run_command(f'python3 scripts/stock_db.py --full --workers {workers}')
        elif answer['mode'] == 'specific':
            date = inquirer.text(message="请输入日期(YYYY-MM-DD)")
            workers = inquirer.text(message="请输入并发数(默认20)")
            workers = workers.strip() or "20"
            if date.strip():
                self.run_command(f'python3 scripts/stock_db.py --date {date} --workers {workers}')
    
    def clean_menu(self):
        """数据清理菜单"""
        self.clear_screen()
        print("=== 数据清理 ===\n")
        
        questions = [
            inquirer.List('mode',
                message="请选择清理模式",
                choices=[
                    ('清理指定日期前数据', 'before_date'),
                    ('清理指定日期数据', 'specific_date'),
                    ('清理所有数据', 'all'),
                    ('返回上级菜单', 'back')
                ]
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if answer['mode'] == 'before_date':
            date = inquirer.text(message="请输入日期(YYYY-MM-DD)")
            if date.strip():
                confirm = inquirer.confirm(
                    message=f"确定要清理 {date} 之前的所有数据吗？",
                    default=False
                )
                if confirm:
                    self.run_command(f'python3 scripts/clean_data.py --before {date}')
        elif answer['mode'] == 'specific_date':
            date = inquirer.text(message="请输入日期(YYYY-MM-DD)")
            if date.strip():
                confirm = inquirer.confirm(
                    message=f"确定要清理 {date} 的数据吗？",
                    default=False
                )
                if confirm:
                    self.run_command(f'python3 scripts/clean_data.py --date {date}')
        elif answer['mode'] == 'all':
            confirm = inquirer.confirm(
                message="确定要清理所有数据吗？此操作不可恢复！",
                default=False
            )
            if confirm:
                self.run_command('python3 scripts/clean_data.py --all')
    
    def maintain_menu(self):
        """系统维护菜单"""
        self.clear_screen()
        print("=== 系统维护 ===\n")
        
        questions = [
            inquirer.List('action',
                message="请选择维护操作",
                choices=[
                    ('错误日志查看', 'logs'),
                    ('返回上级菜单', 'back')
                ]
            )
        ]
        
        answer = inquirer.prompt(questions)
        
        if answer['action'] == 'logs':
            self.run_command('tail -f logs/error.log')

if __name__ == "__main__":
    try:
        cli = AdminCLI()
        cli.main_menu()
    except KeyboardInterrupt:
        print("\n\n程序已退出")
        sys.exit(0) 