"""
数据库模型 - 文件编号与归档系统
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'file_archive.db')


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库，创建所有表"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 文件编号记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_code TEXT NOT NULL,
            file_number TEXT UNIQUE NOT NULL,
            file_type TEXT NOT NULL,
            applicant TEXT NOT NULL,
            apply_date DATE NOT NULL,
            status TEXT DEFAULT '待归档',
            archiver TEXT,
            archive_date DATE,
            archive_path TEXT,
            creator_token TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 序号计数器表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS serial_counter (
            year INTEGER NOT NULL,
            file_code TEXT NOT NULL,
            last_number INTEGER DEFAULT 0,
            PRIMARY KEY (year, file_code)
        )
    ''')
    
    # 文件类型规则表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_type TEXT UNIQUE NOT NULL,
            file_code TEXT UNIQUE NOT NULL,
            number_pattern TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            template_name TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 访问令牌表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_tokens (
            token TEXT PRIMARY KEY,
            partner_name TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 错误日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            error_type TEXT NOT NULL,
            error_message TEXT NOT NULL,
            file_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("数据库初始化完成")


def init_default_rules():
    """初始化默认文件规则"""
    default_rules = [
        {
            'file_type': 'Calibration Standard List',
            'file_code': 'CSL',
            'number_pattern': 'DRA-{year}-{seq:03d}',
            'storage_path': r'D:\workshop\设备档案\医疗器械实验室\设备周期检查记录',
            'template_name': 'CDC-FROM-0047'
        },
        {
            'file_type': 'Incoming Inspection Record',
            'file_code': 'IIR',
            'number_pattern': 'IIR-{year}-{seq:03d}',
            'storage_path': r'D:\workshop\设备档案\医疗器械实验室\设备进货记录',
            'template_name': 'CDC-FROM-0032'
        },
        {
            'file_type': 'User Requirement Specification',
            'file_code': 'URS',
            'number_pattern': 'URS-{year}-{seq:03d}',
            'storage_path': r'D:\workshop\设备档案\医疗器械实验室\其他',
            'template_name': 'CDC-FROM-0017'
        },
        {
            'file_type': 'Installation Qualification',
            'file_code': 'IQ',
            'number_pattern': 'IQ-{year}-{seq:03d}',
            'storage_path': r'D:\workshop\设备档案\医疗器械实验室\设备质量记录',
            'template_name': 'CDC-FROM-0002'
        },
        {
            'file_type': 'Bill Of Material',
            'file_code': 'BOM',
            'number_pattern': 'BOM-{year}-{seq:03d}',
            'storage_path': r'D:\workshop\技术档案\材料清单',
            'template_name': 'CDC-FROM-0013'
        },
        {
            'file_type': 'Quality Project Plan',
            'file_code': 'QPP',
            'number_pattern': 'QPP-{year}-{seq:03d}',
            'storage_path': r'D:\workshop\质量管理体系\质量工程计划',
            'template_name': 'CDC-FROM-0014'
        }
    ]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for rule in default_rules:
        cursor.execute('''
            INSERT OR IGNORE INTO file_rules 
            (file_type, file_code, number_pattern, storage_path, template_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (rule['file_type'], rule['file_code'], rule['number_pattern'], 
              rule['storage_path'], rule['template_name']))
    
    conn.commit()
    conn.close()
    print(f"已初始化 {len(default_rules)} 条默认规则")


def init_admin_token(admin_token: str):
    """初始化管理员令牌"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT OR REPLACE INTO access_tokens (token, partner_name, is_admin)
        VALUES (?, ?, ?)
    ''', (admin_token, '管理员', 1))
    
    conn.commit()
    conn.close()
    print("管理员令牌已设置")


# ==================== 文件记录操作 ====================

def create_file_record(file_code: str, file_type: str, applicant: str, 
                       apply_date: str, creator_token: str) -> Dict:
    """
    创建文件编号记录
    
    Returns:
        包含file_number的字典
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取当前年份
        year = datetime.now().year
        
        # 获取或创建计数器
        cursor.execute('''
            SELECT last_number FROM serial_counter 
            WHERE year = ? AND file_code = ?
        ''', (year, file_code))
        
        result = cursor.fetchone()
        if result:
            last_number = result['last_number']
        else:
            last_number = 0
            cursor.execute('''
                INSERT INTO serial_counter (year, file_code, last_number)
                VALUES (?, ?, ?)
            ''', (year, file_code, 0))
        
        # 新序号
        new_seq = last_number + 1
        
        # 检查是否跳号（手动插入导致）
        cursor.execute('''
            SELECT MAX(CAST(SUBSTR(file_number, -3) AS INTEGER)) as max_seq
            FROM file_records
            WHERE file_code = ? AND apply_date LIKE ?
        ''', (file_code, f'{year}%'))
        
        max_result = cursor.fetchone()
        if max_result and max_result['max_seq'] and max_result['max_seq'] > last_number:
            raise ValueError(f"检测到跳号，数据库最大序号为 {max_result['max_seq']}，计数器为 {last_number}")
        
        # 生成完整编号
        file_number = f"{file_code}-{year}-{new_seq:03d}"
        
        # 插入记录
        cursor.execute('''
            INSERT INTO file_records 
            (file_code, file_number, file_type, applicant, apply_date, creator_token, status)
            VALUES (?, ?, ?, ?, ?, ?, '待归档')
        ''', (file_code, file_number, file_type, applicant, apply_date, creator_token))
        
        # 更新计数器
        cursor.execute('''
            UPDATE serial_counter SET last_number = ?
            WHERE year = ? AND file_code = ?
        ''', (new_seq, year, file_code))
        
        conn.commit()
        
        return {
            'id': cursor.lastrowid,
            'file_number': file_number,
            'file_type': file_type,
            'applicant': applicant,
            'apply_date': apply_date,
            'status': '待归档'
        }
        
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_file_records(keyword: str = '', status: str = '', page: int = 1, 
                     limit: int = 20) -> Tuple[List[Dict], int]:
    """
    获取文件记录列表
    
    Returns:
        (记录列表, 总数量)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 构建查询条件
    conditions = []
    params = []
    
    if keyword:
        conditions.append('''
            (file_number LIKE ? OR file_type LIKE ? OR applicant LIKE ?)
        ''')
        like_keyword = f'%{keyword}%'
        params.extend([like_keyword, like_keyword, like_keyword])
    
    if status:
        conditions.append('status = ?')
        params.append(status)
    
    where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''
    
    # 查询总数
    count_sql = f'SELECT COUNT(*) as total FROM file_records {where_clause}'
    cursor.execute(count_sql, params)
    total = cursor.fetchone()['total']
    
    # 查询记录
    offset = (page - 1) * limit
    sql = f'''
        SELECT * FROM file_records
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    '''
    cursor.execute(sql, params + [limit, offset])
    
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return records, total


def get_file_record_by_id(record_id: int) -> Optional[Dict]:
    """根据ID获取单条记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM file_records WHERE id = ?', (record_id,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None


def get_file_record_by_number(file_number: str) -> Optional[Dict]:
    """根据编号获取记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM file_records WHERE file_number = ?', (file_number,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None


def update_archive_status(record_id: int, archiver: str, archive_path: str) -> bool:
    """更新归档状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE file_records 
        SET status = '已归档', archiver = ?, archive_date = ?, archive_path = ?, updated_at = ?
        WHERE id = ?
    ''', (archiver, datetime.now().strftime('%Y-%m-%d'), archive_path, 
          datetime.now().strftime('%Y-%m-%d %H:%M:%S'), record_id))
    
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    
    return updated


def update_file_record(record_id: int, data: Dict, creator_token: str) -> bool:
    """更新文件记录（仅创建者可编辑）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查权限
    cursor.execute('SELECT creator_token FROM file_records WHERE id = ?', (record_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        return False
    
    if row['creator_token'] != creator_token:
        # 检查是否为管理员
        cursor.execute('SELECT is_admin FROM access_tokens WHERE token = ?', (creator_token,))
        admin_row = cursor.fetchone()
        if not admin_row or not admin_row['is_admin']:
            conn.close()
            return False
    
    # 更新记录
    allowed_fields = ['applicant', 'apply_date']
    updates = []
    params = []
    
    for field in allowed_fields:
        if field in data:
            updates.append(f'{field} = ?')
            params.append(data[field])
    
    if updates:
        params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        params.append(record_id)
        
        sql = f'''
            UPDATE file_records 
            SET {', '.join(updates)}, updated_at = ?
            WHERE id = ?
        '''
        cursor.execute(sql, params)
        conn.commit()
    
    conn.close()
    return True


# ==================== 文件规则操作 ====================

def get_file_rules(active_only: bool = True) -> List[Dict]:
    """获取所有文件规则"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if active_only:
        cursor.execute('SELECT * FROM file_rules WHERE is_active = 1 ORDER BY file_type')
    else:
        cursor.execute('SELECT * FROM file_rules ORDER BY file_type')
    
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return rules


def get_file_rule_by_code(file_code: str) -> Optional[Dict]:
    """根据文件代码获取规则"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM file_rules WHERE file_code = ? AND is_active = 1', (file_code,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None


def get_file_rule_by_type(file_type: str) -> Optional[Dict]:
    """根据文件类型获取规则"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM file_rules WHERE file_type = ? AND is_active = 1', (file_type,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None


def add_file_rule(file_type: str, file_code: str, number_pattern: str, 
                  storage_path: str, template_name: str = '') -> bool:
    """添加新文件规则"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO file_rules (file_type, file_code, number_pattern, storage_path, template_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (file_type, file_code, number_pattern, storage_path, template_name))
        
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def update_file_rule(rule_id: int, data: Dict) -> bool:
    """更新文件规则"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    allowed_fields = ['file_type', 'file_code', 'number_pattern', 'storage_path', 
                      'template_name', 'is_active']
    updates = []
    params = []
    
    for field in allowed_fields:
        if field in data:
            updates.append(f'{field} = ?')
            params.append(data[field])
    
    if updates:
        params.append(rule_id)
        sql = f'UPDATE file_rules SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(sql, params)
        conn.commit()
    
    conn.close()
    return True


# ==================== 令牌验证 ====================

def verify_token(token: str) -> Optional[Dict]:
    """验证令牌有效性"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM access_tokens WHERE token = ?', (token,))
    row = cursor.fetchone()
    
    conn.close()
    return dict(row) if row else None


def create_partner_token(partner_name: str) -> str:
    """创建合作伙伴令牌"""
    import uuid
    
    token = str(uuid.uuid4())
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO access_tokens (token, partner_name, is_admin)
        VALUES (?, ?, 0)
    ''', (token, partner_name))
    
    conn.commit()
    conn.close()
    
    return token


# ==================== 错误日志 ====================

def add_error_log(error_type: str, error_message: str, file_name: str = None):
    """添加错误日志"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO error_logs (error_type, error_message, file_name)
        VALUES (?, ?, ?)
    ''', (error_type, error_message, file_name))
    
    conn.commit()
    conn.close()


def get_error_logs(limit: int = 50) -> List[Dict]:
    """获取错误日志"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM error_logs
        ORDER BY created_at DESC
        LIMIT ?
    ''', (limit,))
    
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return logs


# ==================== 统计报表 ====================

def get_statistics() -> Dict:
    """获取统计信息"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 总记录数
    cursor.execute('SELECT COUNT(*) as total FROM file_records')
    total_records = cursor.fetchone()['total']
    
    # 待归档数量
    cursor.execute("SELECT COUNT(*) as pending FROM file_records WHERE status = '待归档'")
    pending_count = cursor.fetchone()['pending']
    
    # 已归档数量
    cursor.execute("SELECT COUNT(*) as archived FROM file_records WHERE status = '已归档'")
    archived_count = cursor.fetchone()['archived']
    
    # 超过7天未归档
    from datetime import timedelta
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) as overdue FROM file_records 
        WHERE status = '待归档' AND apply_date <= ?
    ''', (seven_days_ago,))
    overdue_count = cursor.fetchone()['overdue']
    
    # 本月新增
    current_month = datetime.now().strftime('%Y-%m')
    cursor.execute('''
        SELECT COUNT(*) as this_month FROM file_records 
        WHERE apply_date LIKE ?
    ''', (f'{current_month}%',))
    this_month_count = cursor.fetchone()['this_month']
    
    conn.close()
    
    return {
        'total_records': total_records,
        'pending_count': pending_count,
        'archived_count': archived_count,
        'overdue_count': overdue_count,
        'this_month_count': this_month_count
    }


def get_pending_overdue_records(days: int = 7) -> List[Dict]:
    """获取超过指定天数未归档的记录"""
    from datetime import timedelta
    
    overdue_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM file_records 
        WHERE status = '待归档' AND apply_date <= ?
        ORDER BY apply_date ASC
    ''', (overdue_date,))
    
    records = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return records


if __name__ == '__main__':
    # 测试数据库初始化
    init_database()
    init_default_rules()
    print("数据库初始化测试完成")
