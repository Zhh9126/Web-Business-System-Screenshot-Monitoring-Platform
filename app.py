import os
import sys
import json
import threading
import time
import io
import hashlib
import secrets
import traceback
from functools import wraps

# ---------- 排除 gevent/eventlet 干扰 ----------
os.environ['GEVENT_SUPPORT'] = 'False'
os.environ['EVENTLET_NOGREENDNS'] = 'yes'
for bad_mod in ('gevent', 'eventlet', 'geventwebsocket', 'greenlet'):
    if bad_mod in sys.modules:
        del sys.modules[bad_mod]

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, send_from_directory, jsonify, abort
)
from flask_socketio import SocketIO

# ========== 路径处理 ==========
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'))
app.secret_key = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

if getattr(sys, 'frozen', False):
    DATA_ROOT = os.path.dirname(sys.executable)
else:
    DATA_ROOT = BASE_DIR

UPLOAD_FOLDER = os.path.join(DATA_ROOT, 'uploads')
THUMB_FOLDER = os.path.join(DATA_ROOT, 'thumbs')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMB_FOLDER, exist_ok=True)

# ========== 用户与设备 ==========
USERS_FILE = os.path.join(DATA_ROOT, 'users.json')
DEVICES_FILE = os.path.join(DATA_ROOT, 'devices.json')

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "admin": {"password": hashlib.md5("password".encode()).hexdigest(), "role": "admin"},
        "user1": {"password": hashlib.md5("111111".encode()).hexdigest(), "role": "user"}
    }

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

USERS = load_users()

def load_devices():
    if os.path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_devices(devices):
    with open(DEVICES_FILE, 'w', encoding='utf-8') as f:
        json.dump(devices, f, indent=2, ensure_ascii=False)

DEVICES = load_devices()
devices_lock = threading.Lock()
device_threads = {}
device_stop_events = {}
device_urls = {}
device_fail_count = {}

# ========== Selenium 自动化 ==========
def create_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,800")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option('useAutomationExtension', False)

    if getattr(sys, 'frozen', False):
        # 打包后：从 EXE 所在目录读取 chromedriver.exe
        exe_dir = os.path.dirname(sys.executable)
        driver_path = os.path.join(exe_dir, 'chromedriver.exe')
        if not os.path.exists(driver_path):
            raise FileNotFoundError(
                f"chromedriver.exe 未找到，请将其放在 EXE 同级目录:\n{driver_path}"
            )
        service = Service(executable_path=driver_path)
    else:
        # 开发环境：自动下载匹配的 ChromeDriver
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(30)
    driver.implicitly_wait(5)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def auto_detect_elements(driver):
    try:
        username_input = password_input = None
        for inp in driver.find_elements(By.TAG_NAME, "input"):
            t = inp.get_attribute("type")
            if t == "password":
                password_input = inp
            elif t in ("text", "email", "tel", None):
                if username_input is None:
                    username_input = inp
                if inp.get_attribute("name") and "user" in inp.get_attribute("name").lower():
                    username_input = inp
        if password_input is None:
            password_input = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        submit_btn = None
        for btn in driver.find_elements(By.CSS_SELECTOR, "button, input[type='submit']"):
            text = (btn.text or btn.get_attribute("value") or "").lower()
            if any(kw in text for kw in ["登录", "登入", "sign in", "login", "submit"]):
                submit_btn = btn
                break
        if submit_btn is None:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        return username_input, password_input, submit_btn
    except:
        return None, None, None

def do_login(device_cfg):
    driver = None
    url = device_cfg['url']
    print(f"[{device_cfg['id']}] 准备访问 {url}")
    try:
        driver = create_driver(device_cfg.get("headless", True))
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        if device_cfg.get("username_selector"):
            u = driver.find_element(By.CSS_SELECTOR, device_cfg["username_selector"])
            p = driver.find_element(By.CSS_SELECTOR, device_cfg["password_selector"])
            s = driver.find_element(By.CSS_SELECTOR, device_cfg["submit_selector"])
        else:
            u, p, s = auto_detect_elements(driver)
            if not all([u, p, s]):
                raise Exception("自动探测登录元素失败，请手动填写选择器")

        u.clear(); u.send_keys(device_cfg["username"])
        p.clear(); p.send_keys(device_cfg["password"])
        s.click()

        if device_cfg.get("success_indicator"):
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, device_cfg["success_indicator"]))
            )
        else:
            time.sleep(5)
        print(f"[{device_cfg['id']}] 登录成功，当前URL: {driver.current_url}")
        return driver, True
    except Exception as e:
        print(f"[{device_cfg['id']}] 登录异常: {e}")
        if driver: driver.quit()
        return None, False

def take_web_screenshot(driver):
    return Image.open(io.BytesIO(driver.get_screenshot_as_png()))

def save_and_notify(device_id, img, owner):
    user_dir = os.path.join(UPLOAD_FOLDER, owner, device_id)
    thumb_dir = os.path.join(THUMB_FOLDER, owner, device_id)
    os.makedirs(user_dir, exist_ok=True)
    os.makedirs(thumb_dir, exist_ok=True)

    timestamp = int(time.time())
    filename = f"{timestamp}.png"
    img.save(os.path.join(user_dir, filename), format='PNG')
    thumb = img.copy()
    thumb.thumbnail((200, 150))
    thumb.save(os.path.join(thumb_dir, filename), format='PNG')
    socketio.emit('new_image', {
        'user': owner,
        'device_id': device_id,
        'filename': filename,
        'timestamp': timestamp
    })
    img.close()
    thumb.close()
    print(f"[{device_id}] ✅ 截图已保存: {filename}")

def device_capture_loop(device_id, stop_event):
    driver = None
    fail_count = 0
    # 使用固定频率调度，确保间隔精确
    next_time = time.time()
    while not stop_event.is_set():
        try:
            with devices_lock:
                if device_id not in DEVICES:
                    break
                cfg = DEVICES[device_id].copy()
            interval = cfg.get("interval", 60)

            # 连续失败保护
            if fail_count >= 3:
                print(f"[{device_id}] 连续失败 {fail_count} 次，进入保护休眠10分钟")
                stop_event.wait(600)
                fail_count = 0
                continue

            # 关闭旧的浏览器
            if driver:
                try: driver.quit()
                except: pass
                driver = None

            new_driver, ok = do_login(cfg)
            if not ok or new_driver is None:
                fail_count += 1
                # 失败后仍按间隔等待，但跳过本次截图
                next_time += interval
                sleep_time = next_time - time.time()
                if sleep_time > 0:
                    stop_event.wait(sleep_time)
                else:
                    next_time = time.time() + interval
                continue

            driver = new_driver
            time.sleep(3)
            current_url = driver.current_url
            device_urls[device_id] = current_url
            img = take_web_screenshot(driver)
            save_and_notify(device_id, img, cfg["owner"])
            fail_count = 0

            # 计算下次截图的时间点
            next_time += interval
            sleep_time = next_time - time.time()
            if sleep_time > 0:
                print(f"[{device_id}] 将在 {sleep_time:.1f} 秒后开始下次截图（设定间隔 {interval} 秒）")
                stop_event.wait(sleep_time)
            else:
                # 本次耗时过长，立即开始下一次，并重置基准
                print(f"[{device_id}] 本次耗时超过设定间隔，立即开始下次截图")
                next_time = time.time() + interval

        except Exception as e:
            print(f"[{device_id}] 循环异常: {e}")
            if driver:
                try: driver.quit()
                except: pass
            driver = None
            fail_count += 1
            next_time += interval
            sleep_time = next_time - time.time()
            if sleep_time > 0:
                stop_event.wait(sleep_time)
            else:
                next_time = time.time() + interval

def start_device_thread(device_id):
    with devices_lock:
        if device_id in device_threads and device_threads[device_id].is_alive():
            return
        if device_id not in DEVICES:
            return
        stop_event = threading.Event()
        device_stop_events[device_id] = stop_event
        t = threading.Thread(target=device_capture_loop, args=(device_id, stop_event), daemon=True)
        device_threads[device_id] = t
        t.start()

def stop_device_thread(device_id):
    with devices_lock:
        if device_id in device_stop_events:
            device_stop_events[device_id].set()
        if device_id in device_threads:
            device_threads[device_id].join(timeout=5)
            del device_threads[device_id]
            del device_stop_events[device_id]

def reload_all_devices():
    for device_id in list(DEVICES.keys()):
        start_device_thread(device_id)

# ========== 认证装饰器 ==========
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get('role') != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return wrapper

# ========== 路由 ==========
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed = hashlib.md5(password.encode()).hexdigest()
        if username in USERS and USERS[username]['password'] == hashed:
            session['user'] = username
            session['role'] = USERS[username]['role']
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="用户名或密码错误")
    return render_template('login.html')

@app.route('/')
@login_required
def dashboard():
    user = session['user']
    if session['role'] == 'admin':
        user_devices = DEVICES
    else:
        user_devices = {k: v for k, v in DEVICES.items() if v['owner'] == user}
    return render_template('dashboard.html', username=user, devices=user_devices, is_admin=(session['role']=='admin'))

@app.route('/monitor/<device_id>')
@login_required
def monitor(device_id):
    if device_id not in DEVICES:
        abort(404)
    cfg = DEVICES[device_id]
    if session['role'] != 'admin' and cfg['owner'] != session['user']:
        abort(403)
    return render_template('monitor.html', device_id=device_id, device_name=cfg['name'], username=session['user'])

@app.route('/admin/devices')
@login_required
@admin_required
def admin_devices():
    return render_template('admin_devices.html', devices=DEVICES)

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    return render_template('admin_users.html', users=USERS)

# ========== 设备管理 API ==========
@app.route('/api/devices', methods=['GET'])
@login_required
@admin_required
def api_get_devices():
    with devices_lock:
        return jsonify(json.loads(json.dumps(DEVICES)))

@app.route('/api/devices', methods=['POST'])
@login_required
@admin_required
def api_add_device():
    data = request.json
    if not data: return jsonify({"error":"No data"}), 400
    device_id = data.get('id')
    if not device_id: return jsonify({"error":"Missing device id"}), 400
    with devices_lock:
        if device_id in DEVICES: return jsonify({"error":"Device ID exists"}), 400
    cfg = {
        "id": device_id,
        "name": data.get("name", device_id),
        "owner": data.get("owner", session['user']),
        "url": data.get("url", ""),
        "username": data.get("username", ""),
        "password": data.get("password", ""),
        "interval": int(data.get("interval", 120)),
        "headless": data.get("headless", True),
        "username_selector": data.get("username_selector", ""),
        "password_selector": data.get("password_selector", ""),
        "submit_selector": data.get("submit_selector", ""),
        "success_indicator": data.get("success_indicator", "")
    }
    with devices_lock:
        DEVICES[device_id] = cfg
        save_devices(DEVICES)
    start_device_thread(device_id)
    return jsonify({"status":"ok", "device":cfg})

@app.route('/api/devices/<device_id>', methods=['PUT'])
@login_required
@admin_required
def api_update_device(device_id):
    with devices_lock:
        if device_id not in DEVICES: return jsonify({"error":"Device not found"}), 404
    data = request.json
    if not data: return jsonify({"error":"No data"}), 400
    with devices_lock:
        cfg = DEVICES[device_id]
        for field in ["name","owner","url","username","password","interval","headless","username_selector","password_selector","submit_selector","success_indicator"]:
            if field in data: cfg[field] = data[field]
        save_devices(DEVICES)
    stop_device_thread(device_id)
    start_device_thread(device_id)
    return jsonify({"status":"ok", "device":cfg})

@app.route('/api/devices/<device_id>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_device(device_id):
    with devices_lock:
        if device_id not in DEVICES: return jsonify({"error":"Device not found"}), 404
    stop_device_thread(device_id)
    with devices_lock:
        del DEVICES[device_id]
        save_devices(DEVICES)
    return jsonify({"status":"ok"})

# ========== 用户管理 API ==========
@app.route('/api/users', methods=['GET'])
@login_required
@admin_required
def api_get_users():
    return jsonify({u: {"role": v["role"]} for u, v in USERS.items()})

@app.route('/api/users', methods=['POST'])
@login_required
@admin_required
def api_add_user():
    data = request.json
    name = data.get('username','').strip()
    pwd = data.get('password','')
    role = data.get('role','user')
    if not name or not pwd: return jsonify({"error":"用户名和密码必填"}), 400
    if name in USERS: return jsonify({"error":"用户已存在"}), 400
    USERS[name] = {"password": hashlib.md5(pwd.encode()).hexdigest(), "role": role}
    save_users(USERS)
    return jsonify({"status":"ok"})

@app.route('/api/users/<username>', methods=['PUT'])
@login_required
@admin_required
def api_update_user(username):
    if username not in USERS: return jsonify({"error":"用户不存在"}), 404
    data = request.json
    if 'password' in data and data['password']:
        USERS[username]['password'] = hashlib.md5(data['password'].encode()).hexdigest()
    if 'role' in data:
        USERS[username]['role'] = data['role']
    save_users(USERS)
    return jsonify({"status":"ok"})

@app.route('/api/users/<username>', methods=['DELETE'])
@login_required
@admin_required
def api_delete_user(username):
    if username not in USERS: return jsonify({"error":"用户不存在"}), 404
    if username == 'admin': return jsonify({"error":"不能删除admin"}), 403
    del USERS[username]
    save_users(USERS)
    return jsonify({"status":"ok"})

@app.route('/api/device_url/<device_id>')
@login_required
def get_device_url(device_id):
    if device_id not in DEVICES: abort(404)
    cfg = DEVICES[device_id]
    if session['role'] != 'admin' and cfg['owner'] != session['user']: abort(403)
    return jsonify({"url": device_urls.get(device_id, "")})

# ========== 图片 API ==========
@app.route('/api/images/<device_id>')
@login_required
def get_images(device_id):
    if device_id not in DEVICES: return jsonify([])
    cfg = DEVICES[device_id]
    if session['role'] != 'admin' and cfg['owner'] != session['user']: abort(403)
    user_dir = os.path.join(UPLOAD_FOLDER, cfg['owner'], device_id)
    if not os.path.exists(user_dir): return jsonify([])
    images = []
    for f in sorted(os.listdir(user_dir), reverse=True):
        if f.endswith('.png'):
            try:
                ts = int(f.split('.')[0])
                dt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
                images.append({'filename':f,'timestamp':ts,'date':dt})
            except: pass
    return jsonify(images)

@app.route('/image/<device_id>/<filename>')
@login_required
def get_image(device_id, filename):
    if device_id not in DEVICES: abort(404)
    cfg = DEVICES[device_id]
    if session['role'] != 'admin' and cfg['owner'] != session['user']: abort(403)
    return send_from_directory(os.path.join(UPLOAD_FOLDER, cfg['owner'], device_id), filename)

@app.route('/thumb/<device_id>/<filename>')
@login_required
def get_thumb(device_id, filename):
    if device_id not in DEVICES: abort(404)
    cfg = DEVICES[device_id]
    if session['role'] != 'admin' and cfg['owner'] != session['user']: abort(403)
    return send_from_directory(os.path.join(THUMB_FOLDER, cfg['owner'], device_id), filename)

@app.route('/delete/<device_id>/<filename>', methods=['DELETE'])
@login_required
def delete_image(device_id, filename):
    if device_id not in DEVICES: abort(404)
    cfg = DEVICES[device_id]
    if session['role'] != 'admin' and cfg['owner'] != session['user']: abort(403)
    try:
        img_p = os.path.join(UPLOAD_FOLDER, cfg['owner'], device_id, filename)
        if os.path.exists(img_p): os.remove(img_p)
        thumb_p = os.path.join(THUMB_FOLDER, cfg['owner'], device_id, filename)
        if os.path.exists(thumb_p): os.remove(thumb_p)
        socketio.emit('delete_image', {'device_id':device_id, 'filename':filename})
        return jsonify({"status":"success"})
    except Exception as e:
        return jsonify({"error":str(e)}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ========== 启动 ==========
if __name__ == '__main__':
    print("="*50)
    print("  Web 业务系统截图监控平台 v2.3 (固定频率版)")
    print("="*50)
    reload_all_devices()
    socketio.run(app, host='0.0.0.0', port=5001, allow_unsafe_werkzeug=True)