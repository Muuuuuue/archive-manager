# 文件自动整理与编号归档系统

个人文件管理工具组合，自动归档邮件附件并管理文件编号。

## 功能特性

- **文件编号申请**：网页表单自动生成唯一编号
- **自动归档**：监控163邮箱，自动分类下载的附件
- **状态跟踪**：实时查看文件归档状态
- **周报提醒**：每周自动生成报告，提醒超期未归档文件
- **GitHub备份**：自动备份数据库到GitHub

## 系统组成

```
file-archive-system/
├── web_system/          # Flask网页系统
├── file_organizer/      # 文件自动整理程序
└── github_backup/       # GitHub备份脚本
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `config.env.example` 为 `config.env`，填写实际值：

```bash
cp config.env.example config.env
# 编辑 config.env 填写配置
```

主要配置项：
- `EMAIL_USERNAME`: 163邮箱地址
- `EMAIL_PASSWORD`: 163邮箱授权码（不是登录密码）
- `ADMIN_TOKEN`: 管理员访问令牌
- `GITHUB_TOKEN`: GitHub Personal Access Token

### 3. 初始化数据库

```bash
cd web_system
python -c "from models import init_database, init_default_rules; init_database(); init_default_rules()"
```

### 4. 启动网页系统

```bash
cd web_system
python app.py
```

访问地址：http://localhost:5000/?token=你的管理员令牌

### 5. 启动文件整理程序

```bash
cd file_organizer

# 手动执行一次
python main.py once

# 启动定时调度器（后台运行）
python main.py scheduler
```

## 使用说明

### 生成合作伙伴访问链接

1. 使用管理员令牌登录管理后台
2. 在"生成合作伙伴令牌"区域输入合作伙伴名称
3. 点击"生成令牌"
4. 复制生成的链接发送给合作伙伴

### 文件编号申请流程

1. 合作伙伴点击访问链接进入系统
2. 点击"文件编号申请"
3. 选择文件类型，填写申请人信息
4. 系统自动生成编号（如：DRA-2026-001）
5. 将编号作为文件名发送邮件

### 自动归档流程

1. 发送邮件到163邮箱，主题包含"文件归档"
2. 附件文件名使用申请的编号
3. 系统每小时自动检查邮箱
4. 自动分类文件到对应文件夹
5. 更新数据库状态为"已归档"

## 文件规则表

| 文件类型 | 文件代码 | 编号格式 | 存储路径 |
|----------|----------|----------|----------|
| Calibration Standard List | CSL | DRA-年份-流水号 | D:\workshop\设备档案\医疗器械实验室\设备周期检查记录 |
| Incoming Inspection Record | IIR | IIR-年份-流水号 | D:\workshop\设备档案\医疗器械实验室\设备进货记录 |
| User Requirement Specification | URS | URS-年份-流水号 | D:\workshop\设备档案\医疗器械实验室\其他 |
| Installation Qualification | IQ | IQ-年份-流水号 | D:\workshop\设备档案\医疗器械实验室\设备质量记录 |
| Bill Of Material | BOM | BOM-年份-流水号 | D:\workshop\技术档案\材料清单 |
| Quality Project Plan | QPP | QPP-年份-流水号 | D:\workshop\质量管理体系\质量工程计划 |

## 技术栈

- **后端**: Python Flask + SQLite
- **前端**: Bootstrap 5
- **邮件**: imaplib + smtplib
- **Excel**: pandas + openpyxl
- **Git**: GitPython

## 许可证

MIT License
