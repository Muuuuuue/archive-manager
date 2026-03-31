"""
周报生成模块 - 生成Excel报告并发送邮件
"""
import os
import sys
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

import pandas as pd

# 添加web_system到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_system'))

from config import EMAIL_CONFIG, REPORT_CONFIG, PATH_CONFIG
from models import get_file_records, get_pending_overdue_records, get_statistics


def generate_weekly_report():
    """
    生成周报Excel文件
    
    Returns:
        报告文件路径
    """
    # 获取统计数据
    stats = get_statistics()
    
    # 获取本周归档记录
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_start_str = week_start.strftime('%Y-%m-%d')
    
    # 获取本周已归档记录
    archived_records, _ = get_file_records(status='已归档', page=1, limit=1000)
    archived_this_week = [
        r for r in archived_records 
        if r['archive_date'] and r['archive_date'] >= week_start_str
    ]
    
    # 获取超期未归档记录
    overdue_records = get_pending_overdue_records(days=REPORT_CONFIG['reminder_days'])
    
    # 创建Excel文件
    report_filename = f"周报_{today.strftime('%Y%m%d')}.xlsx"
    report_path = os.path.join(PATH_CONFIG['temp_folder'], report_filename)
    
    with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
        # Sheet 1: 概览
        overview_data = {
            '指标': ['总记录数', '待归档数', '已归档数', f'≥{REPORT_CONFIG["reminder_days"]}天未归档', '本周新增'],
            '数量': [
                stats['total_records'],
                stats['pending_count'],
                stats['archived_count'],
                stats['overdue_count'],
                stats['this_month_count']
            ]
        }
        overview_df = pd.DataFrame(overview_data)
        overview_df.to_excel(writer, sheet_name='概览', index=False)
        
        # Sheet 2: 本周已归档
        if archived_this_week:
            archived_df = pd.DataFrame(archived_this_week)
            archived_df = archived_df[['file_number', 'file_type', 'applicant', 'apply_date', 'archive_date', 'archive_path']]
            archived_df.columns = ['文件编号', '文件类型', '申请人', '申请日期', '归档日期', '归档路径']
            archived_df.to_excel(writer, sheet_name='本周已归档', index=False)
        else:
            pd.DataFrame({'提示': ['本周暂无归档记录']}).to_excel(writer, sheet_name='本周已归档', index=False)
        
        # Sheet 3: 超期未归档
        if overdue_records:
            overdue_df = pd.DataFrame(overdue_records)
            overdue_df = overdue_df[['file_number', 'file_type', 'applicant', 'apply_date']]
            overdue_df.columns = ['文件编号', '文件类型', '申请人', '申请日期']
            overdue_df.to_excel(writer, sheet_name='超期未归档', index=False)
        else:
            pd.DataFrame({'提示': [f'暂无≥{REPORT_CONFIG["reminder_days"]}天未归档记录']}).to_excel(writer, sheet_name='超期未归档', index=False)
    
    print(f"周报已生成: {report_path}")
    return report_path


def send_weekly_report(report_path):
    """
    发送周报邮件
    
    Args:
        report_path: 报告文件路径
    
    Returns:
        是否成功
    """
    try:
        # 创建邮件
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['username']
        msg['To'] = REPORT_CONFIG['weekly_report_email']
        msg['Subject'] = f"文件归档周报 - {datetime.now().strftime('%Y年%m月%d日')}"
        
        # 邮件正文
        body = f"""
        <html>
        <body>
            <h3>文件归档周报</h3>
            <p>报告日期: {datetime.now().strftime('%Y年%m月%d日')}</p>
            <p>详见附件Excel报告。</p>
            <hr>
            <p style="color: #666; font-size: 12px;">此邮件由系统自动发送</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(body, 'html'))
        
        # 添加附件
        with open(report_path, 'rb') as f:
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(f.read())
        
        encoders.encode_base64(attachment)
        attachment.add_header(
            'Content-Disposition',
            f'attachment; filename= {os.path.basename(report_path)}'
        )
        msg.attach(attachment)
        
        # 发送邮件
        server = smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], 465)
        server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        print(f"周报已发送至: {REPORT_CONFIG['weekly_report_email']}")
        return True
        
    except Exception as e:
        print(f"发送周报失败: {e}")
        return False


def run_weekly_report():
    """运行周报任务"""
    print("\n" + "="*50)
    print("开始生成周报...")
    print("="*50)
    
    report_path = generate_weekly_report()
    send_weekly_report(report_path)
    
    print("="*50 + "\n")


if __name__ == '__main__':
    # 测试
    run_weekly_report()
