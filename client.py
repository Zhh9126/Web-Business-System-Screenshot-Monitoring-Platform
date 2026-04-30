import time
import base64
import io
import requests
import pyautogui

# === 配置信息 ===
SERVER_URL = "http://你的服务器IP:5000"  # 修改为你的服务端地址
API_KEY = "admin_key_abc123"              # 对应设备归属用户的 API Key
DEVICE_ID = "device1"                     # 需要上传的设备ID
INTERVAL = 10                             # 截图间隔（秒）

def capture_and_upload():
    while True:
        try:
            # 截图
            screenshot = pyautogui.screenshot()
            # 转为 base64
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            # 发送 POST
            payload = {
                'device_id': DEVICE_ID,
                'image': f"data:image/png;base64,{img_base64}",
                'api_key': API_KEY
            }
            resp = requests.post(f"{SERVER_URL}/upload", data=payload)
            if resp.status_code == 200:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 上传成功")
            else:
                print(f"上传失败: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"发生异常: {e}")
        time.sleep(INTERVAL)

if __name__ == '__main__':
    print("屏幕截图客户端已启动")
    print(f"服务器: {SERVER_URL}")
    print(f"设备ID: {DEVICE_ID}，间隔: {INTERVAL}秒")
    capture_and_upload()