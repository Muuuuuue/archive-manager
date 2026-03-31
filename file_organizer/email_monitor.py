"""
邮件监控模块 - 检查163邮箱并下载附件
"""
import imaplib
import email
import os
import re
from email.header import decode_header
from datetime import datetime, timedelta
from config import EMAIL_CONFIG, PATH_CONFIG

PROCESSED_FLAG = 'ProcessedByArchive'


def decode_str(s):
    """解码邮件主题/发件人"""
    if not s:
        return ''
    try:
        parts = decode_header(s)
    except Exception:
        return str(s)

    decoded = []
    for value, charset in parts:
        if isinstance(value, bytes):
            # 某些邮件会返回 unknown-8bit 等异常编码，这里做兼容兜底
            if not charset or str(charset).lower() in ('unknown-8bit', 'unknown'):
                charset = 'utf-8'
            try:
                decoded.append(value.decode(charset, errors='replace'))
            except Exception:
                try:
                    decoded.append(value.decode('gb18030', errors='replace'))
                except Exception:
                    decoded.append(value.decode('latin-1', errors='replace'))
        else:
            decoded.append(str(value))
    return ''.join(decoded)


def connect_imap():
    """连接IMAP服务器"""
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_CONFIG['imap_server'])
        mail.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
        return mail
    except Exception as e:
        print(f"IMAP连接失败: {e}")
        return None


def _format_imap_since_date(days=7):
    """生成 IMAP SINCE 查询日期（如 31-Mar-2026）"""
    since_date = datetime.now() - timedelta(days=days)
    return since_date.strftime('%d-%b-%Y')


def _get_email_flags(mail, email_id):
    """读取邮件 FLAGS"""
    try:
        status, data = mail.fetch(email_id, '(FLAGS)')
        if status != 'OK' or not data:
            return ''
        raw = data[0]
        if isinstance(raw, tuple):
            raw = raw[0]
        if isinstance(raw, bytes):
            raw = raw.decode(errors='ignore')
        return str(raw)
    except Exception:
        return ''


def mark_as_processed(mail, email_id):
    """给邮件打处理标记（无论是否匹配关键词）"""
    try:
        # 自定义 IMAP keyword，避免重复扫描
        mail.store(email_id, '+FLAGS', PROCESSED_FLAG)
    except Exception as e:
        print(f"标记邮件处理标签失败: {e}")


def search_emails(mail, subject_keyword='文件归档'):
    """
    搜索符合条件的邮件
    
    Args:
        mail: IMAP连接对象
        subject_keyword: 主题关键词
    
    Returns:
        邮件ID列表
    """
    try:
        # 必须先成功选择邮箱，IMAP状态才会从 AUTH 进入 SELECTED
        status, select_data = mail.select('INBOX')
        if status != 'OK':
            detail = ''
            if select_data and len(select_data) > 0:
                detail = select_data[0].decode(errors='ignore')
            if detail:
                print(f"选择收件箱失败: {detail}")
                if 'Unsafe Login' in detail:
                    print("检测到 163 邮箱拦截（Unsafe Login）。")
                    print("请在 163 邮箱设置中开启 IMAP/SMTP，并确认客户端授权码有效。")
            print("尝试使用 INBOX 只读模式...")
            status, select_data = mail.select('INBOX', readonly=True)
            if status != 'OK':
                detail = ''
                if select_data and len(select_data) > 0:
                    detail = select_data[0].decode(errors='ignore')
                if detail:
                    print(f"只读模式选择收件箱失败: {detail}")
                print("无法选择 INBOX，终止本次搜索")
                return []
        
        # 仅检索最近7天，且未被本程序处理过的邮件
        since_str = _format_imap_since_date(days=7)
        status, data = mail.search(None, 'SINCE', since_str, 'NOT', 'KEYWORD', PROCESSED_FLAG)
        if status != 'OK' or not data:
            # 某些邮箱服务对 KEYWORD 支持有限，降级到仅按日期搜索并在代码中过滤
            status, data = mail.search(None, 'SINCE', since_str)
        if status != 'OK' or not data:
            print("搜索邮件失败或无返回数据")
            return []
        
        email_ids = data[0].split()
        matching_ids = []
        
        for email_id in email_ids:
            try:
                # 二次过滤：跳过已经打过处理标签的邮件
                flags = _get_email_flags(mail, email_id)
                if PROCESSED_FLAG in flags:
                    continue

                _, msg_data = mail.fetch(email_id, '(RFC822)')
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # 解码主题
                subject = decode_str(msg['Subject'])
                
                # 检查主题是否包含关键词
                if subject_keyword in subject:
                    matching_ids.append(email_id)
                
                # 不论是否匹配关键词，都标记为已处理，避免下次重复扫描
                mark_as_processed(mail, email_id)
                    
            except Exception as e:
                print(f"处理邮件 {email_id} 时出错: {e}")
                continue
        
        return matching_ids
        
    except Exception as e:
        print(f"搜索邮件失败: {e}")
        return []


def download_attachments(mail, email_id, download_folder):
    """
    下载邮件的所有附件
    
    Args:
        mail: IMAP连接对象
        email_id: 邮件ID
        download_folder: 下载文件夹
    
    Returns:
        下载的文件列表
    """
    downloaded_files = []
    
    try:
        _, msg_data = mail.fetch(email_id, '(RFC822)')
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        # 获取邮件主题
        subject = decode_str(msg['Subject'])
        print(f"处理邮件: {subject}")
        
        # 遍历邮件内容
        for part in msg.walk():
            # 跳过multipart容器
            if part.get_content_maintype() == 'multipart':
                continue
            
            # 检查是否有附件
            if part.get('Content-Disposition') is None:
                continue
            
            # 获取文件名
            filename = part.get_filename()
            if filename:
                # 解码文件名
                filename = decode_str(filename)
                
                # 清理文件名（移除非法字符）
                filename = re.sub(r'[\\/*?:"<>|]', '_', filename)
                
                # 下载文件
                filepath = os.path.join(download_folder, filename)
                
                # 如果文件已存在，添加序号
                counter = 1
                original_filepath = filepath
                while os.path.exists(filepath):
                    name, ext = os.path.splitext(original_filepath)
                    filepath = f"{name}_{counter}{ext}"
                    counter += 1
                
                with open(filepath, 'wb') as f:
                    f.write(part.get_payload(decode=True))
                
                downloaded_files.append({
                    'filename': filename,
                    'filepath': filepath,
                    'email_subject': subject
                })
                
                print(f"  下载附件: {filename}")
        
        return downloaded_files
        
    except Exception as e:
        print(f"下载附件失败: {e}")
        return []


def mark_as_read(mail, email_id):
    """标记邮件为已读"""
    try:
        mail.store(email_id, '+FLAGS', '\\Seen')
    except Exception as e:
        print(f"标记邮件已读失败: {e}")


def check_and_download_emails():
    """
    主函数：检查邮箱并下载附件
    
    Returns:
        下载的文件列表
    """
    all_downloaded_files = []
    
    # 连接IMAP
    mail = connect_imap()
    if not mail:
        return all_downloaded_files
    
    try:
        # 搜索邮件
        email_ids = search_emails(mail)
        print(f"找到 {len(email_ids)} 封符合条件的邮件")
        
        # 下载附件
        for email_id in email_ids:
            files = download_attachments(mail, email_id, PATH_CONFIG['temp_folder'])
            all_downloaded_files.extend(files)
            
            # 标记为已读
            mark_as_read(mail, email_id)
        
        print(f"共下载 {len(all_downloaded_files)} 个附件")
        
    except Exception as e:
        print(f"处理邮件时出错: {e}")
    
    finally:
        # 关闭连接
        try:
            # 只有在 SELECTED 状态下 close 才有效，失败时忽略
            try:
                mail.close()
            except Exception:
                pass
            mail.logout()
        except:
            pass
    
    return all_downloaded_files


if __name__ == '__main__':
    # 测试
    files = check_and_download_emails()
    print(f"\n下载的文件:")
    for f in files:
        print(f"  - {f['filename']}")
