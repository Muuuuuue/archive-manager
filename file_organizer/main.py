"""
文件自动整理程序 - 主入口
"""
import sys
import os

# 添加web_system到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_system'))

def run_once():
    """运行一次（手动执行）"""
    print("\n" + "="*50)
    print("文件自动整理程序 - 手动执行")
    print("="*50 + "\n")
    
    from email_monitor import check_and_download_emails
    from file_classifier import process_all_files
    
    # 检查并下载邮件
    downloaded_files = check_and_download_emails()
    
    if downloaded_files:
        # 处理下载的文件
        process_all_files()
    else:
        print("\n没有新邮件需要处理")
    
    print("\n" + "="*50)
    print("执行完成")
    print("="*50 + "\n")


def run_scheduler():
    """启动定时调度器"""
    from scheduler import run_scheduler as _run_scheduler
    _run_scheduler()


def run_weekly_report():
    """生成周报"""
    from weekly_report import run_weekly_report as _run_weekly_report
    _run_weekly_report()


def show_help():
    """显示帮助信息"""
    print("""
文件自动整理程序

用法:
    python main.py [命令]

命令:
    once        运行一次（检查邮件并处理附件）
    scheduler   启动定时调度器（每小时检查邮件）
    report      生成并发送周报
    help        显示帮助信息

示例:
    python main.py once         # 手动执行一次
    python main.py scheduler    # 启动后台服务
    python main.py report       # 生成周报
""")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='文件自动整理程序')
    parser.add_argument('command', nargs='?', default='once', 
                        choices=['once', 'scheduler', 'report', 'help'],
                        help='执行命令')
    
    args = parser.parse_args()
    
    if args.command == 'once':
        run_once()
    elif args.command == 'scheduler':
        run_scheduler()
    elif args.command == 'report':
        run_weekly_report()
    else:
        show_help()
