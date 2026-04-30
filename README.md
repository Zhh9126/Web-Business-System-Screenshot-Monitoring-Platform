# 📷 Web 业务系统截图监控平台

一个基于 Python Flask + Selenium 的 Web 业务系统自动截图与远程监控工具。

---

## ✨ 功能亮点

- 🔍 **自动登录截图**：使用无头 Chrome 自动登录业务系统，定时截取页面。
- 📊 **多业务并行监控**：支持同时监控多个业务系统，独立配置间隔与登录信息。
- 👥 **多用户隔离**：管理员可管理所有设备与用户；普通用户只看到自己的设备。
- 📁 **历史截图浏览**：网页端查看历史截图、下载原图、自由删除。
- ⚡ **实时推送**：WebSocket 实时通知新截图（或轮询方式）。
- 🛠️ **Web 管理面板**：完全通过网页管理设备、用户，无需修改代码。
- 📦 **单文件打包**：支持 PyInstaller 打包为独立 EXE，便于离线部署。

---

## 🖥️ 界面截图

（此处可放置截图，例如登录页、仪表盘、监控页、设备管理等）

---

## 🛠️ 技术栈

| 分类 | 技术 |
|------|------|
| 后端 | Python 3, Flask, Flask-SocketIO |
| 前端 | HTML5, CSS3, JavaScript (jQuery / Fetch) |
| 浏览器自动化 | Selenium, ChromeDriver, webdriver-manager (开发) |
| 图像处理 | Pillow |
| 打包部署 | PyInstaller (可选) |

---

## 📦 快速开始（开发模式）

### 环境要求
- Python 3.8+
- Google Chrome 浏览器

### 安装依赖
```bash
git clone https://github.com/Zhh9126/Web-Business-System-Screenshot-Monitoring-Platform.git
cd Web-Business-System-Screenshot-Monitoring-Platform
pip install -r requirements.txt
```

`requirements.txt` 内容：
```text
flask
flask-socketio
pillow
selenium
webdriver-manager
```

### 启动服务
```bash
python app.py
```

服务默认运行在 `http://localhost:5000`。

---

## 🔐 默认账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | password | 管理员 |
| user1 | 111111 | 普通用户 |

---

## 🚀 使用指南

1. **登录**  
   用管理员账号登录后，点击「设备管理」进入管理界面。

2. **添加监控设备**  
   填写设备 ID、名称、归属用户、目标网站 URL、登录账号密码、截图间隔等。  
   可指定自定义的 CSS 选择器用于定位登录表单（留空则自动探测）。

3. **启动监控**  
   保存设备后，后台线程立即开始定时截图，新截图会实时推送到监控页面。

4. **查看截图**  
   返回仪表盘，点击对应设备的「实时监控」进入监控视图，左侧历史列表动态更新。

5. **用户管理**  
   管理员可通过「用户管理」页面新增、编辑、删除用户。

---

## 📁 项目结构

```
screen-monitor/
├── app.py                    # 主程序
├── requirements.txt          # Python 依赖
├── templates/                # 前端模板
│   ├── login.html
│   ├── dashboard.html
│   ├── monitor.html
│   ├── admin_devices.html
│   └── admin_users.html
├── uploads/                  # 截图原图（自动创建）
├── thumbs/                   # 缩略图（自动创建）
├── devices.json              # 设备配置（自动生成）
├── users.json                # 用户配置（自动生成）
└── chromedriver.exe          # （打包时需准备的本地驱动）
```

---

## 🧪 打包为独立 EXE（可选）

1. **确认本地 Chrome 版本，并下载对应 `chromedriver.exe`**  
   放入项目根目录。

2. **执行打包命令**  
```bash
python -m PyInstaller --onefile --console --name "ScreenMonitor" ^
    --add-data "templates;templates" ^
    --hidden-import flask_socketio ^
    --hidden-import engineio.async_drivers.threading ^
    --hidden-import PIL._imaging ^
    --hidden-import selenium.webdriver.common.by ^
    --hidden-import selenium.webdriver.chrome.webdriver ^
    --hidden-import selenium.webdriver.chrome.options ^
    --hidden-import selenium.webdriver.chrome.service ^
    --hidden-import selenium.webdriver.support.ui ^
    --hidden-import selenium.webdriver.support.expected_conditions ^
    --exclude-module gevent ^
    --exclude-module eventlet ^
    --exclude-module greenlet ^
    --exclude-module geventwebsocket ^
    app.py
```

3. **部署**  
   将生成的 `dist/ScreenMonitor.exe` 与 `chromedriver.exe` 放在同一目录，双击运行即可。

---

## ⚠️ 注意事项

- 目标网站必须有可供自动登录的界面，不支持验证码、二次认证等复杂场景（可自行扩展）。
- 请遵守相关法律法规，仅用于监控**自己拥有权限**的系统，勿用于非法用途。
- 推荐在内网环境或专有网络中使用。
- 打包后的 EXE 要求目标电脑安装 Chrome 浏览器，且版本与 `chromedriver.exe` 匹配。

---

## 📝 更新日志

- `v2.3` 固定频率截图、连续失败保护、完全 Web 管理界面。
- `v2.0` 重构为无客户端模式，服务端集成 Selenium 自动截图。
- `v1.0` 初版，客户端-服务器模式。

---

## 🤝 贡献

欢迎提交 Issue 或 Pull Request。

---

## 📄 许可证

MIT License

---

## 📧 联系方式

如有问题，可通过 GitHub Issues 联系作者。

---

**享受自动化监控的便利吧！**
