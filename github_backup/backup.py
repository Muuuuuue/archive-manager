"""
GitHub备份脚本 - 自动备份数据库到GitHub
"""
import os
import sys
import time
from datetime import datetime

from git import Repo, GitCommandError

# 添加web_system到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_system'))

from config import PATH_CONFIG


def get_repo():
    """获取Git仓库对象"""
    repo_path = os.path.join(os.path.dirname(__file__), '..')
    
    try:
        repo = Repo(repo_path)
        return repo
    except Exception as e:
        print(f"无法获取Git仓库: {e}")
        return None


def backup_to_github():
    """
    备份数据库到GitHub
    
    Returns:
        是否成功
    """
    repo = get_repo()
    if not repo:
        return False
    
    try:
        # 检查是否有变更
        if not repo.is_dirty(untracked_files=True):
            print("没有需要备份的变更")
            return True
        
        # 添加数据库文件
        db_path = PATH_CONFIG['db_path']
        if os.path.exists(db_path):
            repo.git.add(db_path)
            print(f"已添加: {db_path}")
        
        # 提交
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        commit_message = f"Auto backup: {timestamp}"
        
        repo.index.commit(commit_message)
        print(f"已提交: {commit_message}")
        
        # 推送
        origin = repo.remote('origin')
        origin.push()
        print("已推送到GitHub")
        
        return True
        
    except GitCommandError as e:
        print(f"Git操作失败: {e}")
        return False
    except Exception as e:
        print(f"备份失败: {e}")
        return False


def run_backup_scheduler():
    """启动备份调度器"""
    import schedule
    
    print("\n" + "="*50)
    print("GitHub备份调度器")
    print("="*50)
    print("\n已配置任务:")
    print("  - 每小时备份一次数据库")
    print("\n按 Ctrl+C 停止程序\n")
    
    # 每小时备份一次
    schedule.every().hour.do(backup_to_github)
    
    # 立即执行一次
    backup_to_github()
    
    # 主循环
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='GitHub备份工具')
    parser.add_argument('command', nargs='?', default='once',
                        choices=['once', 'scheduler'],
                        help='执行命令')
    
    args = parser.parse_args()
    
    if args.command == 'once':
        backup_to_github()
    elif args.command == 'scheduler':
        run_backup_scheduler()
