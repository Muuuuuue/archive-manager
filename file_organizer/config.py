"""
配置文件 - 文件自动整理程序
"""
import os

# 加载环境变量
def load_config():
    """从配置文件加载环境变量"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.env')
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_config()

# 邮箱配置
EMAIL_CONFIG = {
    'imap_server': os.getenv('EMAIL_IMAP_SERVER', 'imap.163.com'),
    'smtp_server': os.getenv('EMAIL_SMTP_SERVER', 'smtp.163.com'),
    'username': os.getenv('EMAIL_USERNAME', ''),
    'password': os.getenv('EMAIL_PASSWORD', ''),
}

# 文件路径配置
PATH_CONFIG = {
    'temp_folder': os.getenv('TEMP_FOLDER', r'D:\temp\file_archive'),
    'pending_folder': os.getenv('PENDING_FOLDER', r'D:\temp\file_archive\pending'),
    'db_path': os.path.join(os.path.dirname(__file__), '..', 'web_system', 'data', 'file_archive.db'),
    'rules_excel': os.path.join(os.path.dirname(__file__), 'data', 'classification_rules.xlsx'),
}

# 周报配置
REPORT_CONFIG = {
    'weekly_report_email': os.getenv('WEEKLY_REPORT_EMAIL', 'yiyao_liu2003@163.com'),
    'reminder_days': int(os.getenv('REMINDER_DAYS', '7')),
}

# 确保文件夹存在
for path_key in ['temp_folder', 'pending_folder']:
    path = PATH_CONFIG[path_key]
    if path:
        os.makedirs(path, exist_ok=True)
