# screenshot_worker.py
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image as PILImage
import os
import time
import uuid

def take_screenshot(url, login_user, login_pass, upload_folder, thumb_folder, driver_path, socketio=None):
    # Chrome 选项
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 无界面模式
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins-discovery")

    driver = None
    try:
        driver = webdriver.Chrome(executable_path=driver_path, options=chrome_options)
        
        # Step 1: 打开登录页
        socketio.emit('log', {'msg': '正在打开目标系统...'})
        driver.get(url)
        
        # 等待常见登录元素出现（可根据实际系统调整）
        socketio.emit('log', {'msg': '等待登录表单加载...'})
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username")) or
            EC.presence_of_element_located((By.ID, "username")) or
            EC.presence_of_element_located((By.NAME, "login")) or
            EC.presence_of_element_located((By.ID, "login"))
        )

        # 查找用户名输入框
        try:
            user_input = driver.find_element(By.NAME, "username") or driver.find_element(By.ID, "username")
        except:
            try:
                user_input = driver.find_element(By.NAME, "login")
            except:
                user_input = driver.find_element(By.TAG_NAME, "input")  # 降级策略

        user_input.clear()
        user_input.send_keys(login_user)
        socketio.emit('log', {'msg': '已输入用户名'})

        # 查找密码输入框
        try:
            pass_input = driver.find_element(By.NAME, "password") or driver.find_element(By.ID, "password")
        except:
            pass_input = driver.find_element(By.TAG_NAME, "input")  # 降级策略（第二个 input）
            if pass_input.get_attribute("type") != "password":
                inputs = driver.find_elements(By.TAG_NAME, "input")
                for inp in inputs:
                    if inp.get_attribute("type") == "password":
                        pass_input = inp
                        break

        pass_input.clear()
        pass_input.send_keys(login_pass)
        socketio.emit('log', {'msg': '已输入密码'})

        # 查找登录按钮并点击
        try:
            login_btn = driver.find_element(By.XPATH, "//button[contains(text(), '登录')]")
        except:
            try:
                login_btn = driver.find_element(By.XPATH, "//input[@type='submit']")
            except:
                login_btn = driver.find_element(By.TAG_NAME, "button")
        
        login_btn.click()
        socketio.emit('log', {'msg': '正在提交登录...'})

        # 等待登录后页面加载（可自定义等待条件）
        time.sleep(5)  # 简单等待
        socketio.emit('log', {'msg': '登录成功，正在截图...'})

        # 生成文件名
        filename = f"{int(time.time())}_{uuid.uuid4().hex[:6]}.png"
        img_path = os.path.join(upload_folder, filename)
        thumb_path = os.path.join(thumb_folder, filename)

        # 截图
        driver.save_screenshot(img_path)
        socketio.emit('log', {'msg': f'截图已保存: {filename}'})

        # 生成缩略图
        img = PILImage.open(img_path)
        img.thumbnail((300, 200))
        img.save(thumb_path, "PNG")

        return f"/static/uploads/{os.path.basename(upload_folder)}/{filename}", \
               f"/static/thumbs/{os.path.basename(thumb_folder)}/{filename}"

    finally:
        if driver:
            driver.quit()