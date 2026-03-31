"""
任务调度器 - 定时执行任务
"""
import schedule
import time
import sys
import os

# 导入其他模块
from email_monitor import check_and_download_emails
from file_classifier import process_all_files
from weekly_report import run_weekly_report


def check_and_process_emails():
    """检查邮件并处理文件"""
    print("\n" + "="*50)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 开始检查邮件...")
    print("="*50)
    
    # 检查并下载邮件附件
    downloaded_files = check_and_download_emails()
    
    if downloaded_files:
        # 处理下载的文件
        process_all_files()
    else:
        print("没有新邮件需要处理")
    
    print("="*50 + "\n")


def run_scheduler():
    """启动调度器"""
    print("\n" + "="*50)
    print("文件自动整理程序 - 任务调度器")
    print("="*50)
    print("\n已配置任务:")
    print("  - 每小时检查邮件并处理附件")
    print("  - 每周一 08:00 生成并发送周报")
    print("\n按 Ctrl+C 停止程序\n")
    
    # 配置定时任务
    # 每小时执行一次
    schedule.every().hour.do(check_and_process_emails)
    
    # 每周一早上8点执行周报
    schedule.every().monday.at("08:00").do(run_weekly_report)
    
    # 立即执行一次（启动时）
    check_and_process_emails()
    
    # 主循环
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次


if __name__ == '__main__':
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n\n程序已停止")
        sys.exit(0)
