# -*- coding: utf-8 -*-
"""
Ví dụ Server Google OAuth cho Video Translator
Cần cài đặt: pip install flask requests
"""

from flask import Flask, request, jsonify, redirect, session
import secrets
import time
import requests
import threading
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Secret key cho session

# ============================================
# CẤU HÌNH GOOGLE OAUTH
# ============================================

# ============================================
# HƯỚNG DẪN LẤY THÔNG TIN TỪ FILE JSON:
# 1. Mở file JSON bạn đã tải về từ Google Cloud Console
# 2. Tìm "client_id" và "client_secret" trong file
# 3. Copy và paste vào dưới đây
# ============================================

# ============================================
# ⚠️ BẢO MẬT: KHÔNG BAO GIỜ HARDCODE SECRETS TRONG CODE!
# ============================================
# Tất cả thông tin nhạy cảm PHẢI được lấy từ environment variables
# Để set environment variables:
# - Local: Tạo file .env hoặc export trong terminal
# - Production (Render): Set trong dashboard Render
# ============================================

# Kiểm tra môi trường (production hay development)
IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production' or os.getenv('PORT') is not None

# Lấy từ environment variables
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI')

# Kiểm tra các biến bắt buộc
if not GOOGLE_CLIENT_ID:
    if IS_PRODUCTION:
        raise ValueError("❌ GOOGLE_CLIENT_ID chưa được set trong environment variables! Vui lòng cấu hình trong Render Dashboard.")
    else:
        print("⚠️  CẢNH BÁO: GOOGLE_CLIENT_ID chưa được set. Vui lòng tạo file .env hoặc export biến môi trường.")
        print("⚠️  Ví dụ: export GOOGLE_CLIENT_ID='your-client-id'")
        raise ValueError("❌ GOOGLE_CLIENT_ID chưa được set trong environment variables!")

if not GOOGLE_CLIENT_SECRET:
    if IS_PRODUCTION:
        raise ValueError("❌ GOOGLE_CLIENT_SECRET chưa được set trong environment variables! Vui lòng cấu hình trong Render Dashboard.")
    else:
        print("⚠️  CẢNH BÁO: GOOGLE_CLIENT_SECRET chưa được set. Vui lòng tạo file .env hoặc export biến môi trường.")
        print("⚠️  Ví dụ: export GOOGLE_CLIENT_SECRET='your-client-secret'")
        raise ValueError("❌ GOOGLE_CLIENT_SECRET chưa được set trong environment variables!")

if not GOOGLE_REDIRECT_URI:
    if IS_PRODUCTION:
        raise ValueError("❌ GOOGLE_REDIRECT_URI chưa được set trong environment variables! Vui lòng cấu hình trong Render Dashboard.")
    else:
        # Fallback cho local development
        GOOGLE_REDIRECT_URI = "http://localhost:3000/api/google-callback"
        print("⚠️  CẢNH BÁO: GOOGLE_REDIRECT_URI chưa được set, sử dụng giá trị mặc định cho local: http://localhost:3000/api/google-callback")

# ============================================
# LƯU TRỮ TẠM THỜI (Nên dùng Redis trong production)
# ============================================
verification_store = {}  # {code: {email, name, access_token, expires_at}}

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/', methods=['GET'])
def index():
    """Trang chủ - API server, không hiển thị giao diện trong production"""
    if IS_PRODUCTION:
        # Production: Chỉ trả về JSON đơn giản, không lộ thông tin
        return jsonify({
            'service': 'Google OAuth Server',
            'status': 'running',
            'version': '1.0.0',
            'endpoints': {
                'auth': '/api/google-auth',
                'callback': '/api/google-callback',
                'verify': '/api/verify-google-auth',
                'ping': '/ping',
                'check_config': '/api/check-config'
            },
            'note': 'This is an API server. Use the endpoints to interact with the service.'
        }), 200
    else:
        # Development: Hiển thị giao diện để dễ test
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Google OAuth Server - Video Translator (DEV)</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #0066cc;
                }}
                .endpoint {{
                    background: #f0f0f0;
                    padding: 10px;
                    margin: 10px 0;
                    border-left: 4px solid #0066cc;
                }}
                .method {{
                    display: inline-block;
                    padding: 3px 8px;
                    background: #0066cc;
                    color: white;
                    border-radius: 3px;
                    font-weight: bold;
                    margin-right: 10px;
                }}
                .status {{
                    display: inline-block;
                    padding: 5px 10px;
                    background: #4CAF50;
                    color: white;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                .dev-badge {{
                    background: #ff9800;
                    color: white;
                    padding: 5px 10px;
                    border-radius: 5px;
                    font-size: 12px;
                    margin-left: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Google OAuth Server <span class="dev-badge">DEV MODE</span></h1>
                <p class="status">✅ Server đang hoạt động</p>
                <hr>
                <h2>📋 Các Endpoint có sẵn:</h2>
                
                <div class="endpoint">
                    <span class="method">GET</span>
                    <strong>/api/google-auth</strong>
                    <p>Bắt đầu Google OAuth flow - Mở trình duyệt để đăng nhập Google</p>
                    <a href="/api/google-auth" target="_blank">🔗 Test ngay</a>
                </div>
                
                <div class="endpoint">
                    <span class="method">GET</span>
                    <strong>/api/google-callback</strong>
                    <p>Callback từ Google OAuth (tự động được gọi bởi Google)</p>
                </div>
                
                <div class="endpoint">
                    <span class="method">POST</span>
                    <strong>/api/verify-google-auth</strong>
                    <p>Xác minh mã 6 chữ số và đăng ký/đăng nhập</p>
                    <p><small>Body: {{"auth_code": "123456", "machine_id": "..."}}</small></p>
                </div>
                
                <div class="endpoint">
                    <span class="method">GET</span>
                    <strong>/ping</strong>
                    <p>Kiểm tra server có hoạt động không</p>
                    <a href="/ping" target="_blank">🔗 Test ngay</a>
                </div>
                
                <div class="endpoint">
                    <span class="method">GET</span>
                    <strong>/api/check-config</strong>
                    <p>Kiểm tra cấu hình environment variables</p>
                    <a href="/api/check-config" target="_blank">🔗 Test ngay</a>
                </div>
                
                <hr>
                <h2>⚙️ Cấu hình:</h2>
                <p><strong>Client ID:</strong> {GOOGLE_CLIENT_ID[:30] if GOOGLE_CLIENT_ID else 'N/A'}...</p>
                <p><strong>Redirect URI:</strong> {GOOGLE_REDIRECT_URI if GOOGLE_REDIRECT_URI else 'N/A'}</p>
                
                <hr>
                <h2>🧪 Hướng dẫn Test:</h2>
                <ol>
                    <li>Nhấn vào link "Test ngay" ở endpoint <code>/api/google-auth</code></li>
                    <li>Đăng nhập Google và cho phép ứng dụng</li>
                    <li>Bạn sẽ thấy mã xác minh 6 chữ số</li>
                    <li>Nhập mã đó vào ứng dụng Video Translator</li>
                </ol>
                <hr>
                <p style="color: #666; font-size: 12px;">
                    ⚠️ <strong>Lưu ý:</strong> Giao diện này chỉ hiển thị trong môi trường development. 
                    Trong production, endpoint này sẽ trả về JSON.
                </p>
            </div>
        </body>
        </html>
        """

@app.route('/api/google-auth', methods=['GET'])
def google_auth():
    """Bắt đầu Google OAuth flow"""
    try:
        # Tạo state token để bảo mật (tránh CSRF)
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        # Tạo URL đăng nhập Google
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={GOOGLE_CLIENT_ID}&"
            f"redirect_uri={GOOGLE_REDIRECT_URI}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"state={state}&"
            f"access_type=offline&"
            f"prompt=consent"
        )
        
        return redirect(auth_url)
        
    except Exception as e:
        print(f"Error in google_auth: {e}")
        return f"Lỗi: {str(e)}", 500

@app.route('/api/google-callback', methods=['GET'])
def google_callback():
    """Xử lý callback từ Google OAuth"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        # Kiểm tra lỗi
        if error:
            return f"""
            <html>
            <head><title>Lỗi Đăng Nhập</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: red;">❌ Lỗi Đăng Nhập</h1>
                <p>{error}</p>
                <p>Vui lòng thử lại.</p>
            </body>
            </html>
            """, 400
        
        # Kiểm tra state (bảo mật)
        if state != session.get('oauth_state'):
            return "Invalid state token", 400
        
        if not code:
            return "Missing authorization code", 400
        
        # Exchange code lấy access token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': GOOGLE_REDIRECT_URI,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data, timeout=30)
        
        if token_response.status_code != 200:
            return f"Lỗi khi lấy token: {token_response.text}", 500
        
        tokens = token_response.json()
        access_token = tokens.get('access_token')
        
        if not access_token:
            return "Không nhận được access token", 500
        
        # Lấy thông tin user từ Google
        user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {'Authorization': f'Bearer {access_token}'}
        user_response = requests.get(user_info_url, headers=headers, timeout=30)
        
        if user_response.status_code != 200:
            return f"Lỗi khi lấy thông tin user: {user_response.text}", 500
        
        user_info = user_response.json()
        email = user_info.get('email', '')
        name = user_info.get('name', '')
        picture = user_info.get('picture', '')
        
        if not email:
            return "Không lấy được email từ Google", 500
        
        # Tạo mã xác minh 6 chữ số
        verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Lưu thông tin tạm thời (5 phút)
        verification_store[verification_code] = {
            'email': email,
            'name': name,
            'picture': picture,
            'access_token': access_token,
            'expires_at': time.time() + 300  # 5 phút
        }
        
        print(f"[GOOGLE AUTH] User: {email}, Code: {verification_code}")
        
        # Hiển thị mã xác minh cho user
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Đăng Nhập Thành Công</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                    margin: 0;
                }}
                .container {{
                    background: white;
                    color: #333;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    max-width: 500px;
                    margin: 0 auto;
                }}
                h1 {{
                    color: #4CAF50;
                    margin-bottom: 20px;
                }}
                .code {{
                    font-size: 48px;
                    font-weight: bold;
                    color: #0066cc;
                    letter-spacing: 10px;
                    padding: 20px;
                    background: #f0f0f0;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .info {{
                    color: #666;
                    margin: 10px 0;
                }}
                .warning {{
                    color: #ff6600;
                    font-weight: bold;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>✅ Đăng Nhập Thành Công!</h1>
                <p class="info">Email: <strong>{email}</strong></p>
                <p class="info">Tên: <strong>{name}</strong></p>
                <hr>
                <p>Vui lòng nhập mã xác minh sau vào ứng dụng:</p>
                <div class="code">{verification_code}</div>
                <p class="warning">⚠️ Mã có hiệu lực trong 5 phút</p>
                <p style="margin-top: 30px; color: #999; font-size: 12px;">
                    Bạn có thể đóng cửa sổ này sau khi đã nhập mã vào ứng dụng.
                </p>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        print(f"Error in google_callback: {e}")
        return f"""
        <html>
        <head><title>Lỗi</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Lỗi</h1>
            <p>{str(e)}</p>
            <p>Vui lòng thử lại.</p>
        </body>
        </html>
        """, 500

@app.route('/api/verify-google-auth', methods=['POST'])
def verify_google_auth():
    """Xác minh mã và đăng nhập"""
    try:
        data = request.json
        code = data.get('auth_code', '').strip()
        machine_id = data.get('machine_id', '')
        
        if not code:
            return jsonify({
                'success': False,
                'message': 'Vui lòng nhập mã xác minh'
            }), 400
        
        # Kiểm tra mã
        user_data = verification_store.get(code)
        if not user_data:
            return jsonify({
                'success': False,
                'message': 'Mã xác minh không hợp lệ'
            }), 400
        
        # Kiểm tra hết hạn
        if user_data['expires_at'] < time.time():
            del verification_store[code]
            return jsonify({
                'success': False,
                'message': 'Mã xác minh đã hết hạn. Vui lòng đăng nhập lại.'
            }), 400
        
        email = user_data['email']
        name = user_data['name']
        
        # KIỂM TRA MACHINE_ID TRƯỚC KHI ĐĂNG KÝ
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Đánh thức server trước
        try:
            ping_url = "https://web-admin-srt212.onrender.com/ping"
            requests.get(ping_url, timeout=10)
        except:
            pass
        
        # Kiểm tra machine_id đã tồn tại chưa
        check_machine_url = "https://web-admin-srt212.onrender.com/api/check-machine"
        try:
            check_response = requests.post(
                check_machine_url,
                json={"machine_id": machine_id},
                headers=headers,
                timeout=30
            )
            
            if check_response.status_code == 200:
                check_result = check_response.json()
                if check_result.get("exists"):
                    # Machine_id đã tồn tại
                    existing_user = check_result.get("user", {})
                    existing_name = existing_user.get("name", "Người dùng")
                    existing_email = existing_user.get("email", "")
                    last_registered = check_result.get("last_registered", "")
                    can_register_again = check_result.get("can_register_again", False)
                    hours_since_last = check_result.get("hours_since_last", 0)
                    user_count = check_result.get("user_count", 0)
                    
                    # Debug log
                    print(f"[GOOGLE AUTH] Machine ID đã tồn tại:")
                    print(f"[GOOGLE AUTH] - User: {existing_name} ({existing_email})")
                    print(f"[GOOGLE AUTH] - Last registered: {last_registered}")
                    print(f"[GOOGLE AUTH] - Hours since last: {hours_since_last}")
                    print(f"[GOOGLE AUTH] - User count: {user_count}")
                    print(f"[GOOGLE AUTH] - Can register again: {can_register_again}")
                    
                    # Kiểm tra xem email có khớp không - nếu khớp thì cho đăng nhập lại
                    if existing_email.lower() == email.lower():
                        # Email khớp với tài khoản đã tồn tại - Cho phép đăng nhập lại
                        print(f"[GOOGLE AUTH] ✅ Email khớp với tài khoản đã tồn tại: {email}")
                        print(f"[GOOGLE AUTH] Gọi API login để đăng nhập lại...")
                        
                        # Gọi API login để đăng nhập lại
                        login_url = "https://web-admin-srt212.onrender.com/api/login"
                        login_data = {
                            "email": email,
                            "machine_id": machine_id,
                            "login_method": "google_oauth"  # Đánh dấu đăng nhập Google
                        }
                        
                        try:
                            login_response = requests.post(
                                login_url,
                                json=login_data,
                                headers=headers,
                                timeout=30
                            )
                            
                            if login_response.status_code == 200:
                                login_result = login_response.json()
                                if login_result.get("success"):
                                    auth_token = login_result.get("auth_token", "")
                                    user_info = login_result.get("user_info", {})
                                    
                                    print(f"[GOOGLE AUTH] ✅ Đăng nhập lại thành công: {email}")
                                    
                                    # Xóa mã xác minh đã dùng
                                    del verification_store[code]
                                    
                                    return jsonify({
                                        'success': True,
                                        'user_data': {
                                            'email': email,
                                            'name': user_info.get('name', name),
                                            'auth_token': auth_token
                                        },
                                        'auth_token': auth_token,
                                        'message': 'Đăng nhập lại thành công'
                                    })
                                else:
                                    error_msg = login_result.get('message', 'Không thể đăng nhập')
                                    print(f"[GOOGLE AUTH] ❌ Lỗi đăng nhập: {error_msg}")
                                    return jsonify({
                                        'success': False,
                                        'message': f'Không thể đăng nhập: {error_msg}'
                                    }), 400
                            else:
                                error_msg = f'Lỗi server login: {login_response.status_code}'
                                print(f"[GOOGLE AUTH] ❌ {error_msg}")
                                return jsonify({
                                    'success': False,
                                    'message': error_msg
                                }), 400
                        except Exception as login_error:
                            error_msg = f'Lỗi khi gọi API login: {str(login_error)}'
                            print(f"[GOOGLE AUTH] ❌ {error_msg}")
                            return jsonify({
                                'success': False,
                                'message': error_msg
                            }), 500
                    
                    # Email không khớp - Kiểm tra có thể đăng ký thêm không
                    if can_register_again:
                        # Có thể đăng ký thêm (sau 1 ngày)
                        print(f"[GOOGLE AUTH] ✅ Cho phép đăng ký thêm: Đã đủ 24 giờ ({hours_since_last:.2f} giờ) và chưa đủ 2 tài khoản ({user_count})")
                        # Tiếp tục đăng ký
                    else:
                        # Không thể đăng ký thêm
                        remaining_hours = max(0, 24 - hours_since_last) if hours_since_last else 24
                        error_msg = f'Tài khoản "{existing_name}" ({existing_email}) đã được đăng ký trên máy này.\n\n'
                        
                        if hours_since_last < 24:
                            error_msg += f'Bạn chỉ có thể tạo thêm 1 tài khoản sau 1 ngày kể từ lần đăng ký cuối ({last_registered}).\n\nThời gian còn lại: {remaining_hours:.1f} giờ.'
                        elif user_count >= 2:
                            error_msg += f'Đã đạt giới hạn số tài khoản trên máy này (tối đa 2 tài khoản).'
                        else:
                            error_msg += f'Không thể đăng ký thêm.'
                        
                        print(f"[GOOGLE AUTH] ❌ Từ chối đăng ký: {error_msg}")
                        return jsonify({
                            'success': False,
                            'message': error_msg,
                            'existing_user': {
                                'name': existing_name,
                                'email': existing_email
                            }
                        }), 400
                else:
                    # Machine_id chưa tồn tại, có thể đăng ký
                    print(f"[GOOGLE AUTH] Machine ID chưa tồn tại, tiến hành đăng ký: {email}")
            else:
                # Lỗi khi kiểm tra, vẫn tiếp tục đăng ký (fallback)
                print(f"[GOOGLE AUTH] Không thể kiểm tra machine_id, tiếp tục đăng ký: {check_response.status_code}")
        except Exception as check_error:
            # Lỗi khi kiểm tra, vẫn tiếp tục đăng ký (fallback)
            print(f"[GOOGLE AUTH] Lỗi khi kiểm tra machine_id: {str(check_error)}, tiếp tục đăng ký")
        
        # Gửi dữ liệu user lên server admin để đăng ký
        admin_server_url = "https://web-admin-srt212.onrender.com/api/register"
        register_data = {
            "name": name,
            "email": email,
            "phone": "",  # Google OAuth không cung cấp phone
            "machine_id": machine_id,
            "app_version": "1.0.0",
            "login_method": "google_oauth"  # Đánh dấu đăng ký qua Google
        }
        
        try:
            # Gửi dữ liệu đăng ký
            admin_response = requests.post(
                admin_server_url,
                json=register_data,
                headers=headers,
                timeout=30
            )
            
            if admin_response.status_code == 200:
                admin_result = admin_response.json()
                if admin_result.get("success"):
                    print(f"[GOOGLE AUTH] Đã đăng ký user lên server admin: {email}")
                else:
                    error_message = admin_result.get('message', 'Unknown error')
                    print(f"[GOOGLE AUTH] Không thể đăng ký lên server admin: {error_message}")
                    # Trả về lỗi nếu server admin từ chối
                    return jsonify({
                        'success': False,
                        'message': f'Không thể đăng ký: {error_message}'
                    }), 400
            else:
                print(f"[GOOGLE AUTH] Server admin trả về status {admin_response.status_code}")
                return jsonify({
                    'success': False,
                    'message': f'Lỗi server admin: {admin_response.status_code}'
                }), 500
        except Exception as admin_error:
            # Lỗi khi đăng ký
            print(f"[GOOGLE AUTH] Lỗi khi đăng ký lên server admin: {str(admin_error)}")
            return jsonify({
                'success': False,
                'message': f'Không thể kết nối đến server admin: {str(admin_error)}'
            }), 500
        
        # Tạo auth token
        auth_token = secrets.token_urlsafe(32)
        
        # Xóa mã xác minh
        del verification_store[code]
        
        print(f"[GOOGLE AUTH] Verified: {email}")
        
        return jsonify({
            'success': True,
            'user_data': {
                'email': email,
                'name': name
            },
            'auth_token': auth_token
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[GOOGLE AUTH] Error in verify_google_auth: {e}")
        print(f"[GOOGLE AUTH] Traceback: {error_trace}")
        return jsonify({
            'success': False,
            'message': f'Lỗi server: {str(e)}'
        }), 500

@app.route('/ping', methods=['GET'])
def ping():
    """API ping để đánh thức server"""
    return jsonify({'status': 'ok'}), 200

@app.route('/api/check-config', methods=['GET'])
def check_config():
    """Kiểm tra cấu hình environment variables (chỉ hiển thị một phần để bảo mật)"""
    config_status = {
        'has_client_id': bool(GOOGLE_CLIENT_ID),
        'has_client_secret': bool(GOOGLE_CLIENT_SECRET),
        'has_redirect_uri': bool(GOOGLE_REDIRECT_URI),
        'client_id_preview': GOOGLE_CLIENT_ID[:20] + '...' if GOOGLE_CLIENT_ID else None,
        'redirect_uri': GOOGLE_REDIRECT_URI if GOOGLE_REDIRECT_URI else None,
        'is_production': IS_PRODUCTION,
        'status': 'ok' if (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET and GOOGLE_REDIRECT_URI) else 'missing_config'
    }
    return jsonify(config_status), 200

# ============================================
# DỌN DẸP MÃ HẾT HẠN
# ============================================

def cleanup_expired_codes():
    """Xóa các mã đã hết hạn"""
    current_time = time.time()
    expired_codes = [
        code for code, data in verification_store.items()
        if data['expires_at'] < current_time
    ]
    for code in expired_codes:
        del verification_store[code]
    if expired_codes:
        print(f"[CLEANUP] Removed {len(expired_codes)} expired codes")

# Chạy cleanup mỗi phút
def cleanup_worker():
    while True:
        time.sleep(60)  # Mỗi phút
        cleanup_expired_codes()

cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
cleanup_thread.start()

# ============================================
# CHẠY SERVER
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("Google OAuth Server cho Video Translator")
    print("=" * 50)
    print(f"Client ID: {GOOGLE_CLIENT_ID[:20]}...")
    print(f"Redirect URI: {GOOGLE_REDIRECT_URI}")
    print("=" * 50)
    print("\nEndpoints:")
    print("  GET  /api/google-auth")
    print("  GET  /api/google-callback")
    print("  POST /api/verify-google-auth")
    print("  GET  /ping")
    print("\n⚠️  LƯU Ý:")
    print("1. Cập nhật GOOGLE_CLIENT_ID và GOOGLE_CLIENT_SECRET")
    print("2. Cập nhật GOOGLE_REDIRECT_URI trong Google Cloud Console")
    print("3. Đảm bảo redirect URI khớp với cấu hình")
    print("=" * 50)
    
    # Đọc PORT từ environment (Render tự động set PORT)
    PORT = int(os.getenv('PORT', 3000))
    # Tắt debug mode trong production
    DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'
    
    app.run(host='0.0.0.0', port=PORT, debug=DEBUG)

