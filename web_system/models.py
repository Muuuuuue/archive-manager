"""
数据库模型 - 文件编号与归档系统
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'file_archive.db')


def _ensure_column(cursor: sqlite3.Cursor, table_name: str, column_name: str, column_def: str):
    """为旧库补齐字段（幂等）"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing = {row[1] for row in cursor.fetchall()}
    if column_name not in existing:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


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
    _ensure_column(cursor, 'file_records', 'revision_no', 'INTEGER DEFAULT 0')
    _ensure_column(cursor, 'file_records', 'is_voided', 'BOOLEAN DEFAULT 0')
    _ensure_column(cursor, 'file_records', 'voided_at', 'TIMESTAMP')
    _ensure_column(cursor, 'file_records', 'void_reason', 'TEXT')
    _ensure_column(cursor, 'file_records', 'void_requester', 'TEXT')
    _ensure_column(cursor, 'file_records', 'void_approver', 'TEXT')
    _ensure_column(cursor, 'file_records', 'record_action', "TEXT DEFAULT 'NEW'")
    _ensure_column(cursor, 'file_records', 'base_record_id', 'INTEGER')
    _ensure_column(cursor, 'file_records', 'page_count', 'INTEGER')
    
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS delete_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            requester_token TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT '待审核',
            reviewer TEXT,
            review_comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS voided_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            file_number TEXT NOT NULL,
            void_reason TEXT NOT NULL,
            voided_by TEXT NOT NULL,
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


def create_revision_record(base_record_id: int, applicant: str, apply_date: str, operator_token: str) -> Dict:
    """基于已有记录创建升版记录（Rev1.0、Rev2.0...）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM file_records WHERE id = ?', (base_record_id,))
        base = cursor.fetchone()
        if not base:
            raise ValueError('原始记录不存在')

        root_id = base['base_record_id'] if base['base_record_id'] else base_record_id
        cursor.execute('''
            SELECT COALESCE(MAX(revision_no), 0) as max_revision
            FROM file_records
            WHERE id = ? OR base_record_id = ?
        ''', (root_id, root_id))
        current = cursor.fetchone()['max_revision']
        revision_no = int(current) + 1
        revision_number = f"{base['file_number'].split('_Rev')[0]}_Rev{revision_no}.0"

        cursor.execute('''
            INSERT INTO file_records
            (file_code, file_number, file_type, applicant, apply_date, status,
             creator_token, revision_no, record_action, base_record_id)
            VALUES (?, ?, ?, ?, ?, '待归档', ?, ?, 'REVISION', ?)
        ''', (
            base['file_code'], revision_number, base['file_type'],
            applicant, apply_date, operator_token, revision_no, root_id
        ))
        conn.commit()
        return {
            'id': cursor.lastrowid,
            'file_number': revision_number,
            'revision_no': revision_no,
            'status': '待归档'
        }
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def create_delete_request(record_id: int, requester_token: str, reason: str) -> Dict:
    """提交删除申请（所有用户可对任意记录提交审核申请）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM file_records WHERE id = ?', (record_id,))
        record = cursor.fetchone()
        if not record:
            raise ValueError('记录不存在')

        cursor.execute('''
            INSERT INTO delete_requests (record_id, requester_token, reason, status)
            VALUES (?, ?, ?, '待审核')
        ''', (record_id, requester_token, reason))
        conn.commit()
        return {'request_id': cursor.lastrowid, 'status': '待审核'}
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_file_records(keyword: str = '', status: str = '', page: int = 1,
                     limit: int = 20, token: str = '',
                     is_admin: bool = False, file_type: str = '',
                     applicant: str = '', date_start: str = '',
                     date_end: str = '', ids: Optional[List[int]] = None,
                     date_field: str = 'apply_date') -> Tuple[List[Dict], int]:
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
            (file_number LIKE ? OR file_type LIKE ? OR applicant LIKE ? OR file_code LIKE ?)
        ''')
        like_keyword = f'%{keyword}%'
        params.extend([like_keyword, like_keyword, like_keyword, like_keyword])
    
    if status:
        conditions.append('status = ?')
        params.append(status)

    if file_type:
        conditions.append('file_type = ?')
        params.append(file_type)

    if applicant:
        conditions.append('applicant LIKE ?')
        params.append(f'%{applicant}%')

    date_col = 'archive_date' if date_field == 'archive_date' else 'apply_date'
    if date_start:
        conditions.append(f'{date_col} >= ?')
        params.append(date_start)

    if date_end:
        conditions.append(f'{date_col} <= ?')
        params.append(date_end)

    if ids:
        placeholders = ','.join(['?'] * len(ids))
        conditions.append(f'id IN ({placeholders})')
        params.extend(ids)
    
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


def search_records_for_modal(keyword: str = '', page: int = 1, limit: int = 20,
                             only_not_voided: bool = True) -> Tuple[List[Dict], int]:
    """弹窗记录选择查询（按文件类型/文件代码/编号模糊）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    conditions = []
    params = []

    if only_not_voided:
        conditions.append('COALESCE(is_voided, 0) = 0')

    if keyword:
        like_kw = f'%{keyword}%'
        conditions.append('(file_type LIKE ? OR file_code LIKE ? OR file_number LIKE ?)')
        params.extend([like_kw, like_kw, like_kw])

    where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''
    cursor.execute(f'SELECT COUNT(*) as total FROM file_records {where_clause}', params)
    total = cursor.fetchone()['total']

    offset = (page - 1) * limit
    cursor.execute(f'''
        SELECT id, file_number, file_code, file_type, applicant, apply_date, revision_no, is_voided, status
        FROM file_records
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', params + [limit, offset])
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows, total


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


def get_accessible_records(token: str, is_admin: bool = False) -> List[Dict]:
    """获取当前用户可操作记录（升版/删除申请）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    if is_admin:
        cursor.execute('''
            SELECT id, file_number, file_type, applicant, apply_date, revision_no, is_voided
            FROM file_records ORDER BY created_at DESC LIMIT 500
        ''')
    else:
        cursor.execute('''
            SELECT id, file_number, file_type, applicant, apply_date, revision_no, is_voided
            FROM file_records WHERE creator_token = ? ORDER BY created_at DESC LIMIT 500
        ''', (token,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def update_archive_status(record_id: int, archiver: str, archive_path: str, page_count: Optional[int] = None) -> bool:
    """更新归档状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE file_records 
        SET status = '已归档', archiver = ?, archive_date = ?, archive_path = ?, page_count = ?, updated_at = ?
        WHERE id = ?
    ''', (archiver, datetime.now().strftime('%Y-%m-%d'), archive_path, page_count,
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


def search_file_rules(keyword: str = '', page: int = 1, limit: int = 20) -> Tuple[List[Dict], int]:
    """规则分页搜索（文件类型/文件代码模糊）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    conditions = []
    params = []
    if keyword:
        like_kw = f'%{keyword}%'
        conditions.append('(file_type LIKE ? OR file_code LIKE ?)')
        params.extend([like_kw, like_kw])
    where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

    cursor.execute(f'SELECT COUNT(*) as total FROM file_rules {where_clause}', params)
    total = cursor.fetchone()['total']
    offset = (page - 1) * limit
    cursor.execute(f'''
        SELECT * FROM file_rules
        {where_clause}
        ORDER BY file_type
        LIMIT ? OFFSET ?
    ''', params + [limit, offset])
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows, total


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


def get_delete_requests(status: str = '') -> List[Dict]:
    """获取删除申请列表（管理员）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    params = []
    where = ''
    if status:
        where = 'WHERE dr.status = ?'
        params.append(status)
    cursor.execute(f'''
        SELECT dr.*, fr.file_number, fr.file_type, fr.applicant
        FROM delete_requests dr
        LEFT JOIN file_records fr ON fr.id = dr.record_id
        {where}
        ORDER BY dr.created_at DESC
    ''', params)
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def review_delete_request(request_id: int, approved: bool, reviewer: str, review_comment: str = '') -> bool:
    """审核删除申请：通过则作废记录并入作废库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM delete_requests WHERE id = ?', (request_id,))
        req = cursor.fetchone()
        if not req or req['status'] != '待审核':
            return False

        new_status = '已通过' if approved else '已驳回'
        cursor.execute('''
            UPDATE delete_requests
            SET status = ?, reviewer = ?, review_comment = ?, reviewed_at = ?
            WHERE id = ?
        ''', (new_status, reviewer, review_comment, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), request_id))

        if approved:
            cursor.execute('SELECT * FROM file_records WHERE id = ?', (req['record_id'],))
            record = cursor.fetchone()
            if record:
                cursor.execute('''
                    UPDATE file_records
                    SET status = '已作废', is_voided = 1, voided_at = ?, void_reason = ?, void_requester = ?, void_approver = ?, updated_at = ?
                    WHERE id = ?
                ''', (
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    req['reason'],
                    req['requester_token'],
                    reviewer,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    req['record_id']
                ))
                cursor.execute('''
                    INSERT INTO voided_records (record_id, file_number, void_reason, voided_by)
                    VALUES (?, ?, ?, ?)
                ''', (req['record_id'], record['file_number'], req['reason'], reviewer))

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_voided_records() -> List[Dict]:
    """已作废记录库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT vr.*, fr.file_type, fr.applicant
        FROM voided_records vr
        LEFT JOIN file_records fr ON fr.id = vr.record_id
        ORDER BY vr.created_at DESC
    ''')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def restore_voided_record(record_id: int, reviewer: str) -> bool:
    """恢复已作废记录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            UPDATE file_records
            SET status = '待归档', is_voided = 0, voided_at = NULL, void_reason = NULL,
                void_requester = NULL, void_approver = NULL, updated_at = ?
            WHERE id = ?
        ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), record_id))
        if cursor.rowcount <= 0:
            conn.rollback()
            return False
        cursor.execute('DELETE FROM voided_records WHERE record_id = ?', (record_id,))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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


def get_record_detail(record_id: int) -> Optional[Dict]:
    """获取单条记录详情（含作废审核信息）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM file_records WHERE id = ?', (record_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    detail = dict(row)

    cursor.execute('''
        SELECT requester_token, reviewer, reviewed_at
        FROM delete_requests
        WHERE record_id = ? AND status = '已通过'
        ORDER BY reviewed_at DESC, id DESC
        LIMIT 1
    ''', (record_id,))
    req = cursor.fetchone()
    if req:
        detail['void_requester'] = detail.get('void_requester') or req['requester_token']
        detail['void_approver'] = detail.get('void_approver') or req['reviewer']
        detail['voided_at'] = detail.get('voided_at') or req['reviewed_at']

    conn.close()
    return detail


if __name__ == '__main__':
    # 测试数据库初始化
    init_database()
    init_default_rules()
    print("数据库初始化测试完成")
