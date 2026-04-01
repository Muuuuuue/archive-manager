"""
Flask Web应用 - 文件编号与归档系统
"""
import os
import sys
import io
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
import pandas as pd

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

# 导入模型
from models import (
    init_database, init_default_rules, init_admin_token,
    create_file_record, get_file_records, get_file_record_by_id,
    get_file_record_by_number, update_archive_status, update_file_record,
    get_file_rules, get_file_rule_by_code, get_file_rule_by_type,
    add_file_rule, update_file_rule,
    verify_token, create_partner_token,
    add_error_log, get_error_logs,
    get_statistics, get_pending_overdue_records,
    create_revision_record, create_delete_request,
    get_delete_requests, review_delete_request, get_voided_records, restore_voided_record,
    search_records_for_modal, search_file_rules, get_record_detail
)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.urandom(24)

# 配置
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'admin-default-token')


# ==================== 装饰器 ====================

def require_token(f):
    """验证令牌的装饰器"""
    def decorated_function(*args, **kwargs):
        token = request.args.get('token') or request.form.get('token')
        if not token:
            return jsonify({'success': False, 'error': '缺少访问令牌'}), 401
        
        token_info = verify_token(token)
        if not token_info:
            return jsonify({'success': False, 'error': '无效的访问令牌'}), 401
        
        request.token_info = token_info
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function


def require_admin(f):
    """验证管理员权限的装饰器"""
    def decorated_function(*args, **kwargs):
        token = request.args.get('token') or request.form.get('token')
        if not token:
            if request.is_json:
                return jsonify({'success': False, 'error': '缺少访问令牌'}), 401
            else:
                flash('缺少访问令牌', 'error')
                return redirect(url_for('index'))
        
        token_info = verify_token(token)
        if not token_info:
            if request.is_json:
                return jsonify({'success': False, 'error': '无效的访问令牌'}), 401
            else:
                flash('无效的访问令牌', 'error')
                return redirect(url_for('index'))
        
        if not token_info.get('is_admin'):
            if request.is_json:
                return jsonify({'success': False, 'error': '需要管理员权限'}), 403
            else:
                flash('需要管理员权限', 'error')
                return redirect(url_for('index'))
        
        request.token_info = token_info
        request.token = token
        return f(*args, **kwargs)
    
    decorated_function.__name__ = f.__name__
    return decorated_function


# ==================== 页面路由 ====================

@app.route('/')
def index():
    """首页"""
    token = request.args.get('token', '')
    is_admin = False
    
    if token:
        token_info = verify_token(token)
        if token_info:
            is_admin = token_info.get('is_admin', False)
    
    return render_template('index.html', token=token, is_admin=is_admin)


@app.route('/apply')
def apply_page():
    """编号申请页面"""
    token = request.args.get('token', '')
    
    if not token:
        flash('请通过有效链接访问', 'error')
        return redirect(url_for('index'))
    
    token_info = verify_token(token)
    if not token_info:
        flash('无效的访问令牌', 'error')
        return redirect(url_for('index'))
    
    return render_template(
        'apply.html',
        token=token,
        file_types=get_file_rules(active_only=True)
    )


@app.route('/archive')
def archive_page():
    """归档查询页面"""
    token = request.args.get('token', '')
    
    if not token:
        flash('请通过有效链接访问', 'error')
        return redirect(url_for('index'))
    
    token_info = verify_token(token)
    if not token_info:
        flash('无效的访问令牌', 'error')
        return redirect(url_for('index'))
    
    # 获取查询参数
    keyword = request.args.get('keyword', '')
    status = request.args.get('status', '')
    file_type = request.args.get('file_type', '')
    applicant = request.args.get('applicant', '')
    date_start = request.args.get('date_start', '')
    date_end = request.args.get('date_end', '')
    date_field = request.args.get('date_field', 'apply_date')
    page = int(request.args.get('page', 1))
    
    # 获取记录列表
    records, total = get_file_records(
        keyword=keyword,
        status=status,
        page=page,
        limit=20,
        file_type=file_type,
        applicant=applicant,
        date_start=date_start,
        date_end=date_end,
        date_field=date_field
    )
    
    # 计算分页
    total_pages = (total + 19) // 20
    
    return render_template('archive.html', 
                          token=token, 
                          records=records, 
                          total=total,
                          page=page,
                          total_pages=total_pages,
                          keyword=keyword,
                          status=status,
                          file_type=file_type,
                          applicant=applicant,
                          date_start=date_start,
                          date_end=date_end,
                          date_field=date_field,
                          file_types=get_file_rules(active_only=True),
                          is_admin=True)


@app.route('/rules')
@require_admin
def rules_page():
    """规则维护页面（管理员）"""
    token = request.args.get('token', '')
    keyword = request.args.get('keyword', '')
    page = int(request.args.get('page', 1))
    rules, total = search_file_rules(keyword=keyword, page=page, limit=20)
    total_pages = (total + 19) // 20
    return render_template('rules.html', token=token, rules=rules, keyword=keyword,
                           page=page, total=total, total_pages=total_pages)


@app.route('/admin')
@require_admin
def admin_page():
    """管理后台（管理员）"""
    token = request.args.get('token', '')
    
    # 获取统计信息
    stats = get_statistics()
    
    # 获取错误日志
    error_logs = get_error_logs(limit=20)
    
    # 获取超期未归档记录
    overdue_records = get_pending_overdue_records(days=7)
    delete_requests = get_delete_requests(status='待审核')
    voided_records = get_voided_records()
    
    return render_template('admin.html', 
                          token=token, 
                          stats=stats,
                          error_logs=error_logs,
                          overdue_records=overdue_records,
                          delete_requests=delete_requests,
                          voided_records=voided_records)


@app.route('/success')
def success_page():
    """申请成功页面"""
    file_number = request.args.get('file_number', '')
    token = request.args.get('token', '')
    return render_template('success.html', file_number=file_number, token=token)


# ==================== API路由 ====================

@app.route('/api/apply', methods=['POST'])
def api_apply():
    """API：申请文件编号"""
    try:
        data = request.get_json(silent=True) or request.form
        
        # 获取参数
        file_type = data.get('file_type', '').strip()
        applicant = data.get('applicant', '').strip()
        apply_date = data.get('apply_date', '').strip()
        token = data.get('token', '').strip()
        action_type = data.get('action_type', 'new').strip().lower()
        base_record_id = data.get('base_record_id', '').strip()
        delete_reason = data.get('delete_reason', '').strip()
        
        # 验证参数
        if not applicant:
            return jsonify({'success': False, 'error': '请填写申请人姓名'}), 400
        if not apply_date:
            return jsonify({'success': False, 'error': '请选择申请日期'}), 400
        if not token:
            return jsonify({'success': False, 'error': '缺少访问令牌'}), 401
        if action_type == 'new' and not file_type:
            return jsonify({'success': False, 'error': '请选择文件类型'}), 400
        
        # 验证令牌
        token_info = verify_token(token)
        if not token_info:
            return jsonify({'success': False, 'error': '无效的访问令牌'}), 401
        
        if action_type == 'revision':
            if not base_record_id:
                return jsonify({'success': False, 'error': '请选择需要升版的记录'}), 400
            result = create_revision_record(
                base_record_id=int(base_record_id),
                applicant=applicant,
                apply_date=apply_date,
                operator_token=token
            )
        elif action_type == 'delete':
            if not base_record_id:
                return jsonify({'success': False, 'error': '请选择需要删除的记录'}), 400
            if not delete_reason:
                return jsonify({'success': False, 'error': '请填写删除原因'}), 400
            req = create_delete_request(
                record_id=int(base_record_id),
                requester_token=token,
                reason=delete_reason
            )
            return jsonify({'success': True, 'message': '删除申请已提交，等待管理员审核', 'data': req})
        else:
            # 获取文件规则
            rule = get_file_rule_by_type(file_type)
            if not rule:
                return jsonify({'success': False, 'error': '无效的文件类型'}), 400

            # 创建记录
            result = create_file_record(
                file_code=rule['file_code'],
                file_type=file_type,
                applicant=applicant,
                apply_date=apply_date,
                creator_token=token
            )
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        add_error_log('APPLY_ERROR', str(e))
        return jsonify({'success': False, 'error': '系统错误，请重试'}), 500


@app.route('/api/archive', methods=['GET'])
def api_archive():
    """API：获取归档记录列表"""
    try:
        token = request.args.get('token', '')
        if not token:
            return jsonify({'success': False, 'error': '缺少访问令牌'}), 401
        token_info = verify_token(token)
        if not token_info:
            return jsonify({'success': False, 'error': '无效的访问令牌'}), 401

        keyword = request.args.get('keyword', '')
        status = request.args.get('status', '')
        file_type = request.args.get('file_type', '')
        applicant = request.args.get('applicant', '')
        date_start = request.args.get('date_start', '')
        date_end = request.args.get('date_end', '')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        records, total = get_file_records(
            keyword=keyword,
            status=status,
            page=page,
            limit=limit,
            file_type=file_type,
            applicant=applicant,
            date_start=date_start,
            date_end=date_end,
            date_field=request.args.get('date_field', 'apply_date')
        )
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'page': page,
                'limit': limit,
                'items': records
            }
        })
        
    except Exception as e:
        add_error_log('ARCHIVE_QUERY_ERROR', str(e))
        return jsonify({'success': False, 'error': '查询失败'}), 500


@app.route('/api/records/search', methods=['GET'])
def api_search_records():
    """弹窗记录选择：后端分页+模糊搜索"""
    try:
        token = request.args.get('token', '')
        if not token:
            return jsonify({'success': False, 'error': '缺少访问令牌'}), 401
        if not verify_token(token):
            return jsonify({'success': False, 'error': '无效的访问令牌'}), 401

        keyword = request.args.get('keyword', '')
        only_not_voided = request.args.get('only_not_voided', 'true').lower() != 'false'
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        rows, total = search_records_for_modal(
            keyword=keyword,
            page=page,
            limit=limit,
            only_not_voided=only_not_voided
        )
        return jsonify({
            'success': True,
            'data': {'items': rows, 'total': total, 'page': page, 'limit': limit}
        })
    except Exception as e:
        add_error_log('RECORD_SEARCH_ERROR', str(e))
        return jsonify({'success': False, 'error': '查询失败'}), 500


@app.route('/api/archive/export', methods=['GET'])
def api_export_archive():
    """导出归档记录Excel（管理员可导出全部，合作伙伴仅自己）"""
    try:
        token = request.args.get('token', '')
        if not token:
            return jsonify({'success': False, 'error': '缺少访问令牌'}), 401
        if not verify_token(token):
            return jsonify({'success': False, 'error': '无效的访问令牌'}), 401

        keyword = request.args.get('keyword', '')
        status = request.args.get('status', '')
        file_type = request.args.get('file_type', '')
        applicant = request.args.get('applicant', '')
        date_start = request.args.get('date_start', '')
        date_end = request.args.get('date_end', '')
        date_field = request.args.get('date_field', 'apply_date')
        ids_raw = request.args.get('ids', '').strip()
        ids = [int(x) for x in ids_raw.split(',') if x.strip().isdigit()] if ids_raw else None

        records, _ = get_file_records(
            keyword=keyword,
            status=status,
            page=1,
            limit=100000,
            file_type=file_type,
            applicant=applicant,
            date_start=date_start,
            date_end=date_end,
            ids=ids,
            date_field=date_field
        )

        export_rows = []
        for r in records:
            export_rows.append({
                'ID': r.get('id'),
                '文件编号': r.get('file_number'),
                '版本号': f"Rev{int(r.get('revision_no', 0))}.0" if int(r.get('revision_no', 0)) > 0 else '',
                '文件类型': r.get('file_type'),
                '申请人': r.get('applicant'),
                '申请日期': r.get('apply_date'),
                '状态': r.get('status'),
                '归档人': r.get('archiver'),
                '归档日期': r.get('archive_date'),
                '筛选日期字段': '归档日期' if date_field == 'archive_date' else '申请日期',
                '归档路径': r.get('archive_path'),
                '作废原因': r.get('void_reason') or ''
            })

        df = pd.DataFrame(export_rows)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='归档记录')
        output.seek(0)
        filename = f"archive_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(output, as_attachment=True, download_name=filename,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        add_error_log('ARCHIVE_EXPORT_ERROR', str(e))
        return jsonify({'success': False, 'error': '导出失败'}), 500


@app.route('/api/archive/<int:record_id>', methods=['PUT'])
def api_update_archive(record_id):
    """API：更新归档状态"""
    try:
        data = request.get_json(silent=True) or request.form
        token = data.get('token', '')
        archiver = data.get('archiver', '')
        archive_path = data.get('archive_path', '')
        page_count = data.get('page_count')
        
        if not token:
            return jsonify({'success': False, 'error': '缺少访问令牌'}), 401
        
        token_info = verify_token(token)
        if not token_info:
            return jsonify({'success': False, 'error': '无效的访问令牌'}), 401
        
        # 更新归档状态
        page_count_value = None
        if page_count not in (None, ''):
            try:
                page_count_value = int(page_count)
            except Exception:
                page_count_value = None
        success = update_archive_status(record_id, archiver, archive_path, page_count=page_count_value)
        
        if success:
            return jsonify({'success': True, 'message': '归档状态已更新'})
        else:
            return jsonify({'success': False, 'error': '记录不存在'}), 404
            
    except Exception as e:
        add_error_log('ARCHIVE_UPDATE_ERROR', str(e))
        return jsonify({'success': False, 'error': '更新失败'}), 500


@app.route('/api/archive/<int:record_id>/detail', methods=['GET'])
def api_archive_detail(record_id):
    """获取记录详情"""
    try:
        token = request.args.get('token', '')
        if not token:
            return jsonify({'success': False, 'error': '缺少访问令牌'}), 401
        if not verify_token(token):
            return jsonify({'success': False, 'error': '无效的访问令牌'}), 401
        detail = get_record_detail(record_id)
        if not detail:
            return jsonify({'success': False, 'error': '记录不存在'}), 404
        return jsonify({'success': True, 'data': detail})
    except Exception as e:
        add_error_log('ARCHIVE_DETAIL_ERROR', str(e))
        return jsonify({'success': False, 'error': '查询详情失败'}), 500


@app.route('/api/rules', methods=['GET'])
@require_admin
def api_get_rules():
    """API：获取文件规则列表"""
    try:
        keyword = request.args.get('keyword', '')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        rules, total = search_file_rules(keyword=keyword, page=page, limit=limit)
        return jsonify({
            'success': True,
            'data': {'items': rules, 'total': total, 'page': page, 'limit': limit}
        })
    except Exception as e:
        add_error_log('RULES_QUERY_ERROR', str(e))
        return jsonify({'success': False, 'error': '查询失败'}), 500


@app.route('/api/rules', methods=['POST'])
@require_admin
def api_add_rule():
    """API：添加文件规则"""
    try:
        data = request.get_json(silent=True) or request.form
        
        file_type = data.get('file_type', '').strip()
        file_code = data.get('file_code', '').strip().upper()
        number_pattern = data.get('number_pattern', '').strip()
        storage_path = data.get('storage_path', '').strip()
        template_name = data.get('template_name', '').strip()
        
        # 验证参数
        if not file_type:
            return jsonify({'success': False, 'error': '请填写文件类型'}), 400
        if not file_code:
            return jsonify({'success': False, 'error': '请填写文件代码'}), 400
        if not number_pattern:
            return jsonify({'success': False, 'error': '请填写编号规则'}), 400
        if not storage_path:
            return jsonify({'success': False, 'error': '请填写存储路径'}), 400
        
        # 添加规则
        success = add_file_rule(file_type, file_code, number_pattern, storage_path, template_name)
        
        if success:
            return jsonify({'success': True, 'message': '规则添加成功'})
        else:
            return jsonify({'success': False, 'error': '文件类型或代码已存在'}), 400
            
    except Exception as e:
        add_error_log('RULES_ADD_ERROR', str(e))
        return jsonify({'success': False, 'error': '添加失败'}), 500


@app.route('/api/rules/<int:rule_id>', methods=['PUT'])
@require_admin
def api_update_rule(rule_id):
    """API：更新文件规则"""
    try:
        data = request.get_json(silent=True) or request.form
        
        update_data = {}
        if 'file_type' in data:
            update_data['file_type'] = data['file_type']
        if 'file_code' in data:
            update_data['file_code'] = data['file_code'].upper()
        if 'number_pattern' in data:
            update_data['number_pattern'] = data['number_pattern']
        if 'storage_path' in data:
            update_data['storage_path'] = data['storage_path']
        if 'template_name' in data:
            update_data['template_name'] = data['template_name']
        if 'is_active' in data:
            update_data['is_active'] = 1 if data['is_active'] else 0
        
        update_file_rule(rule_id, update_data)
        
        return jsonify({'success': True, 'message': '规则更新成功'})
        
    except Exception as e:
        add_error_log('RULES_UPDATE_ERROR', str(e))
        return jsonify({'success': False, 'error': '更新失败'}), 500


@app.route('/api/statistics', methods=['GET'])
@require_admin
def api_statistics():
    """API：获取统计信息"""
    try:
        stats = get_statistics()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        add_error_log('STATISTICS_ERROR', str(e))
        return jsonify({'success': False, 'error': '获取统计失败'}), 500


@app.route('/api/generate-token', methods=['POST'])
@require_admin
def api_generate_token():
    """API：生成合作伙伴令牌"""
    try:
        data = request.get_json(silent=True) or request.form
        partner_name = data.get('partner_name', '').strip()
        
        if not partner_name:
            return jsonify({'success': False, 'error': '请填写合作伙伴名称'}), 400
        
        token = create_partner_token(partner_name)
        
        return jsonify({
            'success': True,
            'data': {
                'token': token,
                'partner_name': partner_name,
                'url': f'http://localhost:5000/?token={token}'
            }
        })
        
    except Exception as e:
        add_error_log('GENERATE_TOKEN_ERROR', str(e))
        return jsonify({'success': False, 'error': '生成令牌失败'}), 500


@app.route('/api/delete-requests/<int:request_id>/review', methods=['POST'])
@require_admin
def api_review_delete_request(request_id):
    """管理员审核删除申请"""
    try:
        data = request.get_json(silent=True) or request.form
        action = data.get('action', '').strip().lower()
        comment = data.get('comment', '').strip()
        if action not in ('approve', 'reject'):
            return jsonify({'success': False, 'error': '无效操作'}), 400
        ok = review_delete_request(
            request_id=request_id,
            approved=(action == 'approve'),
            reviewer='管理员',
            review_comment=comment
        )
        if not ok:
            return jsonify({'success': False, 'error': '申请不存在或已处理'}), 400
        return jsonify({'success': True, 'message': '审核完成'})
    except Exception as e:
        add_error_log('DELETE_REVIEW_ERROR', str(e))
        return jsonify({'success': False, 'error': '审核失败'}), 500


@app.route('/api/voided-records/<int:record_id>/restore', methods=['POST'])
@require_admin
def api_restore_voided_record(record_id):
    """管理员恢复已作废记录"""
    try:
        ok = restore_voided_record(record_id, reviewer='管理员')
        if not ok:
            return jsonify({'success': False, 'error': '恢复失败，记录不存在'}), 400
        return jsonify({'success': True, 'message': '记录已恢复'})
    except Exception as e:
        add_error_log('VOIDED_RESTORE_ERROR', str(e))
        return jsonify({'success': False, 'error': '恢复失败'}), 500


# ==================== 初始化 ====================

def init_app():
    """初始化应用"""
    # 初始化数据库
    init_database()
    init_default_rules()
    init_admin_token(ADMIN_TOKEN)
    
    print(f"应用初始化完成")
    print(f"管理员令牌: {ADMIN_TOKEN}")
    print(f"管理员访问地址: http://localhost:5000/?token={ADMIN_TOKEN}")


# ==================== 主程序 ====================

if __name__ == '__main__':
    init_app()
    
    host = os.getenv('WEB_HOST', '0.0.0.0')
    port = int(os.getenv('WEB_PORT', 5000))
    debug = os.getenv('WEB_DEBUG', 'false').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)
