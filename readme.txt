pip install --no-index --find-links=offline-packages flask flask-socketio pillow selenium webdriver-manager gevent gevent-websocket
python -m PyInstaller --onefile --noconsole --name "ScreenMonitor" --add-data "templates;templates" --add-data "chromedriver.exe;." --hidden-import flask_socketio --hidden-import engineio.async_drivers.gevent --hidden-import gevent --hidden-import PIL._imaging --hidden-import selenium.webdriver.common.by app.py


# 先清理旧的构建文件
rmdir /s /q build dist
del ScreenMonitor.spec

# 打包（单行）
python -m PyInstaller --onefile --noconsole --name "ScreenMonitor" --add-data "templates;templates"  --hidden-import flask_socketio --hidden-import engineio.async_drivers.threading --hidden-import PIL._imaging --hidden-import selenium.webdriver.common.by --exclude-module gevent --exclude-module eventlet --exclude-module greenlet --exclude-module geventwebsocket app.py


python -m PyInstaller --onefile --console --name "ScreenMonitorDebug" --add-data "templates;templates"  --hidden-import flask_socketio --hidden-import engineio.async_drivers.threading --hidden-import PIL._imaging --hidden-import selenium.webdriver.common.by --exclude-module gevent --exclude-module eventlet --exclude-module greenlet --exclude-module geventwebsocket app.py


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