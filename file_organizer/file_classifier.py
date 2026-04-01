"""
文件分类模块 - 根据文件名分类文件
"""
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime

# 添加web_system到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_system'))

from config import PATH_CONFIG
from models import (
    get_file_rule_by_code, get_file_record_by_number,
    update_archive_status, add_error_log
)


def detect_page_count(file_path):
    """识别页数（优先支持pdf/docx）"""
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.pdf':
            # 不引入额外依赖的简易统计
            with open(file_path, 'rb') as f:
                data = f.read()
            count = len(re.findall(rb'/Type\s*/Page\b', data))
            return count if count > 0 else None
        if ext == '.docx':
            # docx无法稳定获取实际分页，使用app.xml中的Pages作为近似值
            with zipfile.ZipFile(file_path, 'r') as zf:
                if 'docProps/app.xml' in zf.namelist():
                    xml = zf.read('docProps/app.xml').decode('utf-8', errors='ignore')
                    m = re.search(r'<Pages>(\d+)</Pages>', xml)
                    if m:
                        return int(m.group(1))
    except Exception:
        return None
    return None


def parse_file_number(filename):
    """
    从文件名解析文件编号
    
    Args:
        filename: 文件名
    
    Returns:
        dict: {'file_code': 'CSL', 'year': 2026, 'seq': 1} 或 None
    """
    # 移除扩展名
    name = os.path.splitext(filename)[0]
    
    # 匹配格式：CODE-YEAR-SEQ
    # 如：DRA-2026-001, IIR-2026-001, URS-2026-001
    pattern = r'^([A-Z]+)-(\d{4})-(\d{3})(?:_Rev(\d+)\.0)?$'
    match = re.match(pattern, name)
    
    if match:
        return {
            'file_code': match.group(1),
            'year': int(match.group(2)),
            'seq': int(match.group(3)),
            'revision_no': int(match.group(4)) if match.group(4) else 0,
            'full_number': name
        }
    
    return None


def get_target_path(file_code, year):
    """
    根据文件代码获取目标路径
    
    Args:
        file_code: 文件代码
        year: 年份
    
    Returns:
        目标路径 或 None
    """
    # 查询数据库获取规则
    rule = get_file_rule_by_code(file_code)
    
    if not rule:
        return None
    
    # 构建目标路径（添加年份子文件夹）
    base_path = rule['storage_path']
    target_path = os.path.join(base_path, str(year))
    
    return target_path


def move_file(source_path, target_path, filename):
    """
    移动文件到目标路径
    
    Args:
        source_path: 源文件路径
        target_path: 目标文件夹路径
        filename: 文件名
    
    Returns:
        (成功, 目标完整路径, 错误信息)
    """
    try:
        # 确保目标文件夹存在
        os.makedirs(target_path, exist_ok=True)
        
        # 目标文件完整路径
        target_file_path = os.path.join(target_path, filename)
        
        # 检查文件是否已存在（重名移到pending，由人工处理升版）
        if os.path.exists(target_file_path):
            return False, None, f"文件已存在: {target_file_path}"
        
        # 移动文件
        shutil.move(source_path, target_file_path)
        
        return True, target_file_path, None
        
    except Exception as e:
        return False, None, str(e)


def classify_and_move_file(filepath, email_subject=''):
    """
    分类并移动单个文件
    
    Args:
        filepath: 文件完整路径
        email_subject: 来源邮件主题
    
    Returns:
        (成功, 结果信息)
    """
    filename = os.path.basename(filepath)
    
    print(f"处理文件: {filename}")
    
    # 解析文件编号
    file_info = parse_file_number(filename)
    
    if not file_info:
        # 无法解析编号，移动到待分类
        pending_path = PATH_CONFIG['pending_folder']
        os.makedirs(pending_path, exist_ok=True)
        
        target_file = os.path.join(pending_path, filename)
        counter = 1
        original_target = target_file
        while os.path.exists(target_file):
            name, ext = os.path.splitext(original_target)
            target_file = f"{name}_{counter}{ext}"
            counter += 1
        
        shutil.move(filepath, target_file)
        
        error_msg = f"无法解析文件编号: {filename}"
        add_error_log('PARSE_ERROR', error_msg, filename)
        
        return False, error_msg
    
    # 获取目标路径
    target_path = get_target_path(file_info['file_code'], file_info['year'])
    
    if not target_path:
        # 规则未找到，移动到待分类
        pending_path = PATH_CONFIG['pending_folder']
        os.makedirs(pending_path, exist_ok=True)
        
        target_file = os.path.join(pending_path, filename)
        counter = 1
        original_target = target_file
        while os.path.exists(target_file):
            name, ext = os.path.splitext(original_target)
            target_file = f"{name}_{counter}{ext}"
            counter += 1
        
        shutil.move(filepath, target_file)
        
        error_msg = f"未找到文件代码对应的规则: {file_info['file_code']}"
        add_error_log('RULE_NOT_FOUND', error_msg, filename)
        
        return False, error_msg
    
    # 移动文件
    success, target_file_path, error = move_file(filepath, target_path, filename)
    
    if not success:
        # 移动失败（权限或IO等错误）
        pending_path = PATH_CONFIG['pending_folder']
        os.makedirs(pending_path, exist_ok=True)
        
        pending_file = os.path.join(pending_path, filename)
        counter = 1
        original_pending = pending_file
        while os.path.exists(pending_file):
            name, ext = os.path.splitext(original_pending)
            pending_file = f"{name}_{counter}{ext}"
            counter += 1
        
        shutil.move(filepath, pending_file)
        
        add_error_log('MOVE_ERROR', error or '未知错误', filename)
        
        return False, error
    
    # 更新数据库中的归档状态
    record = get_file_record_by_number(file_info['full_number'])
    
    if record:
        page_count = detect_page_count(target_file_path)
        # 更新已有记录
        update_archive_status(
            record_id=record['id'],
            archiver='系统自动归档',
            archive_path=target_file_path,
            page_count=page_count
        )
        print(f"  已更新记录状态: {file_info['full_number']}")
    else:
        # 记录不存在（可能是直接发邮件而没有申请编号）
        print(f"  警告: 未找到对应的申请记录: {file_info['full_number']}")
    
    return True, target_file_path


def process_all_files():
    """
    处理临时文件夹中的所有文件
    
    Returns:
        (成功数, 失败数, 失败列表)
    """
    temp_folder = PATH_CONFIG['temp_folder']
    
    if not os.path.exists(temp_folder):
        print(f"临时文件夹不存在: {temp_folder}")
        return 0, 0, []
    
    # 获取所有文件
    files = [f for f in os.listdir(temp_folder) if os.path.isfile(os.path.join(temp_folder, f))]
    
    if not files:
        print("临时文件夹为空")
        return 0, 0, []
    
    success_count = 0
    fail_count = 0
    fail_list = []
    
    print(f"\n开始处理 {len(files)} 个文件...")
    
    for filename in files:
        filepath = os.path.join(temp_folder, filename)
        success, result = classify_and_move_file(filepath)
        
        if success:
            success_count += 1
            print(f"  [OK] 归档成功: {result}")
        else:
            fail_count += 1
            fail_list.append({'filename': filename, 'error': result})
            print(f"  [FAIL] 归档失败: {result}")
    
    print(f"\n处理完成: 成功 {success_count}, 失败 {fail_count}")
    
    return success_count, fail_count, fail_list


if __name__ == '__main__':
    # 测试
    process_all_files()
