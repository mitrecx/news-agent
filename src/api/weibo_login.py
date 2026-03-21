"""Weibo login automation router"""

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from .models import WeiboLoginRequest, WeiboLoginResponse

router = APIRouter(prefix="/api/weibo", tags=["weibo"])
logger = logging.getLogger(__name__)


def _check_selenium_available() -> bool:
    """检查 Selenium 是否可用"""
    try:
        import undetected_chromedriver
        return True
    except ImportError:
        return False


def _perform_weibo_login_sync(username: str, password: str) -> dict:
    """
    同步执行微博登录（在单独线程中运行）

    Args:
        username: 微博用户名
        password: 微博密码

    Returns:
        dict: {
            'success': bool,
            'cookie': str | None,
            'message': str,
            'error': str | None
        }
    """
    # 延迟导入selenium相关模块，避免启动时因缺少依赖而失败
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import undetected_chromedriver as uc
    except ImportError as e:
        logger.error(f"❌ Selenium 或 undetected_chromedriver 不可用: {e}")
        return {
            'success': False,
            'cookie': None,
            'message': 'Selenium 或 undetected_chromedriver 未安装',
            'error': f'Selenium not available: {str(e)}'
        }

    logger.info(f"🔐 开始微博登录自动化: {username}")

    # 预清理：确保没有残留的 Chrome/ChromeDriver 进程
    try:
        import subprocess
        for process_name in ['chrome', 'chromedriver']:
            result = subprocess.run(
                ["pgrep", "-f", process_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid_str in pids:
                    try:
                        pid = int(pid_str)
                        os.kill(pid, 9)
                        logger.debug(f"🧹 预清理: {process_name} (PID: {pid})")
                    except (ValueError, ProcessLookupError, OSError):
                        pass
        # 等待一下让进程完全退出
        import time
        time.sleep(0.5)
    except Exception as e:
        logger.debug(f"预清理时出错（可忽略）: {e}")

    driver = None

    try:
        # 使用 undetected-chromedriver 启动 Chrome
        import time
        start_time = time.time()
        logger.info("🚀 启动 Chrome 浏览器（使用 undetected-chromedriver）...")

        try:
            # undetected-chromedriver 会自动处理反检测
            options = uc.ChromeOptions()
            options.add_argument('--headless=new')  # 使用新的无头模式
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-dev-tools')
            options.add_argument('--no-zygote')
            options.add_argument('--single-process')
            options.add_argument('--disable-software-rasterizer')
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-infobars')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--remote-debugging-port=9222')

            # 使用系统已安装的 ChromeDriver，避免 SSL 证书问题
            driver_executable_path = '/usr/local/bin/chromedriver'
            
            # 检查 ChromeDriver 是否存在
            if not os.path.exists(driver_executable_path):
                logger.error(f"❌ ChromeDriver 不存在: {driver_executable_path}")
                return {
                    'success': False,
                    'cookie': None,
                    'message': f'ChromeDriver 未找到: {driver_executable_path}',
                    'error': 'ChromeDriver not found'
                }

            logger.info(f"🔧 使用系统 ChromeDriver: {driver_executable_path}")
            
            driver = uc.Chrome(
                options=options,
                version_main=None,
                driver_executable_path=driver_executable_path,
                keep_alive=True,
            )
            elapsed = time.time() - start_time
            logger.info(f"✅ Chrome 浏览器启动成功，耗时: {elapsed:.2f}秒")
        except Exception as e:
            logger.error(f"❌ Chrome 启动失败: {e}")
            return {
                'success': False,
                'cookie': None,
                'message': f'无法启动 Chrome 浏览器: {str(e)}',
                'error': f'Chrome startup failed: {str(e)}'
            }

        # 访问微博登录页面
        login_url = "https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.19)&entry=miniblog"
        logger.info(f"📍 访问登录页面: {login_url}")
        start_time = time.time()
        driver.get(login_url)
        elapsed = time.time() - start_time
        logger.info(f"✅ 页面加载完成，耗时: {elapsed:.2f}秒")

        # 等待页面加载
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        import time
        time.sleep(2)

        # 查找用户名输入框
        logger.info("🔍 查找登录表单...")
        username_input = None
        password_input = None
        submit_button = None

        # 尝试多种选择器
        username_selectors = [
            (By.ID, "swf_username"),
            (By.NAME, "username"),
            (By.CSS_SELECTOR, "input[name='username']"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ]

        password_selectors = [
            (By.ID, "swf_password"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[name='password']"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ]

        submit_selectors = [
            (By.ID, "swf_submit"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.CSS_SELECTOR, "a[node-type='submitBtn']"),
            (By.XPATH, "//a[contains(text(), '登录')]"),
            (By.XPATH, "//input[contains(@value, '登录')]"),
        ]

        # 查找用户名输入框
        for selector_type, selector_value in username_selectors:
            try:
                username_input = driver.find_element(selector_type, selector_value)
                if username_input:
                    logger.debug(f"✓ 找到用户名输入框: {selector_type}={selector_value}")
                    break
            except Exception:
                continue

        # 查找密码输入框
        for selector_type, selector_value in password_selectors:
            try:
                password_input = driver.find_element(selector_type, selector_value)
                if password_input:
                    logger.debug(f"✓ 找到密码输入框: {selector_type}={selector_value}")
                    break
            except Exception:
                continue

        # 查找提交按钮
        for selector_type, selector_value in submit_selectors:
            try:
                submit_button = driver.find_element(selector_type, selector_value)
                if submit_button:
                    logger.debug(f"✓ 找到提交按钮: {selector_type}={selector_value}")
                    break
            except Exception:
                continue

        if not username_input or not password_input:
            logger.error("❌ 未找到登录表单")
            return {
                'success': False,
                'cookie': None,
                'message': '未找到登录表单，页面结构可能已变化',
                'error': 'Login form not found'
            }

        # 输入用户名和密码（模拟人类打字速度）
        logger.info("⌨️  输入登录凭据...")
        username_input.clear()

        # 模拟人类打字：逐个字符输入，随机延迟
        import random
        for char in username:
            username_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))  # 每个字符间隔 50-150ms

        time.sleep(random.uniform(0.5, 1.0))  # 输入完用户名后等待

        password_input.clear()
        for char in password:
            password_input.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))  # 每个字符间隔 50-150ms

        time.sleep(random.uniform(0.5, 1.0))  # 输入完密码后等待

        # 点击登录按钮
        if submit_button:
            logger.info("🖱️  点击登录按钮...")
            submit_button.click()
        else:
            logger.warning("⚠️ 未找到登录按钮，尝试按回车键...")
            from selenium.webdriver.common.keys import Keys
            password_input.send_keys(Keys.RETURN)

        # 等待登录完成（增加等待时间，考虑可能的验证码或二次验证）
        logger.info("⏳ 等待登录完成（可能需要验证码）...")

        # 多次检查登录状态
        login_success = False
        max_wait_time = 15  # 最多等待 15 秒
        check_interval = 2  # 每 2 秒检查一次

        for wait_time in range(0, max_wait_time, check_interval):
            time.sleep(check_interval)
            current_url = driver.current_url
            logger.info(f"⏳ 等待中... {wait_time + check_interval}秒, 当前 URL: {current_url[:100]}...")

            # 检查是否登录成功
            if 'weibo.com' in current_url and 'login' not in current_url and 'passport' not in current_url:
                login_success = True
                logger.info("✅ 检测到登录成功（URL 变化）")
                break

            # 尝试查找登录后的元素
            try:
                search_box = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='搜索'], input[node-type='searchInput']")
                if search_box:
                    login_success = True
                    logger.info("✅ 检测到登录成功（找到搜索框）")
                    break
            except Exception:
                pass

            # 检查是否有验证码或其他验证
            try:
                captcha = driver.find_element(By.CSS_SELECTOR, "input[type='text'][placeholder*='验证'], input[type='text'][placeholder*='码']")
                if captcha:
                    logger.warning("⚠️ 检测到需要验证码，当前自动化无法处理")
                    # 保存截图用于调试
                    try:
                        screenshot_path = "/tmp/weibo_login_debug.png"
                        driver.save_screenshot(screenshot_path)
                        logger.info(f"📸 调试截图已保存: {screenshot_path}")
                    except Exception:
                        pass
                    break
            except Exception:
                pass

        # 最终检查
        current_url = driver.current_url
        logger.info(f"📍 最终 URL: {current_url}")

        if not login_success:
            # 检查是否在 passport 页面（可能需要额外验证）
            if 'passport.weibo.com' in current_url:
                logger.error("❌ 登录失败：页面重定向到 passport.weibo.com，可能需要验证码或二次验证")
                return {
                    'success': False,
                    'cookie': None,
                    'message': '登录失败：微博要求额外验证（如验证码、滑块验证等）。请手动登录一次后再试，或尝试使用其他账号。',
                    'error': 'Login failed: additional verification required'
                }
            else:
                logger.error("❌ 登录失败：未知原因")
                return {
                    'success': False,
                    'cookie': None,
                    'message': '登录失败，请检查用户名和密码，或微博账号状态是否正常',
                    'error': 'Login failed'
                }

        logger.info("✅ 登录成功")

        # 提取 Cookie
        logger.info("🍪 提取 Cookie...")
        cookies = driver.get_cookies()

        # 构建 Cookie 字符串
        cookie_parts = []
        important_cookies = ['SUB', 'SUBP', 'ALF', 'SUHB']

        for cookie in cookies:
            if cookie['name'] in important_cookies:
                cookie_parts.append(f"{cookie['name']}={cookie['value']}")

        cookie_string = '; '.join(cookie_parts)

        if not cookie_string:
            logger.warning("⚠️ 未能提取到有效的 Cookie")
            return {
                'success': False,
                'cookie': None,
                'message': '登录成功但未能提取到 Cookie',
                'error': 'Failed to extract cookie'
            }

        logger.info(f"✅ Cookie 提取成功: {cookie_string[:50]}...")

        return {
            'success': True,
            'cookie': cookie_string,
            'message': '登录成功，Cookie 已提取',
            'error': None
        }

    except Exception as e:
        logger.error(f"❌ 登录过程出错: {e}", exc_info=True)
        return {
            'success': False,
            'cookie': None,
            'message': f'登录过程出错: {str(e)}',
            'error': str(e)
        }

    finally:
        # 清理资源
        if driver:
            try:
                driver.quit()
                logger.info("🧹 浏览器已关闭")
            except Exception:
                pass


async def _update_env_file(cookie: str) -> bool:
    """
    更新 .env 文件中的微博 Cookie

    Args:
        cookie: 新的 Cookie 值

    Returns:
        bool: 是否更新成功
    """
    try:
        env_path = Path(".env")

        if not env_path.exists():
            logger.warning(".env 文件不存在")
            return False

        # 读取现有内容
        content = env_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # 查找并替换 WEIBO_COOKIE 行
        updated = False
        new_lines = []

        for line in lines:
            if line.strip().startswith('WEIBO_COOKIE='):
                new_lines.append(f'WEIBO_COOKIE="{cookie}"')
                updated = True
            else:
                new_lines.append(line)

        # 如果没有找到，添加新行
        if not updated:
            new_lines.append(f'WEIBO_COOKIE="{cookie}"')

        # 写回文件
        env_path.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
        logger.info("✅ .env 文件已更新")
        return True

    except Exception as e:
        logger.error(f"❌ 更新 .env 文件失败: {e}")
        return False


@router.post("/login", response_model=WeiboLoginResponse)
async def weibo_login(request: WeiboLoginRequest):
    """
    微博登录自动化接口

    使用 Selenium 自动登录微博并提取 Cookie

    Args:
        request: 包含用户名和密码的登录请求

    Returns:
        WeiboLoginResponse: 登录结果，包含提取的 Cookie
    """
    logger.info(f"📥 收到微博登录请求: {request.username}")

    # 检查 Selenium 可用性
    if not _check_selenium_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Selenium 不可用，请安装相关依赖: pip install selenium webdriver-manager"
        )

    try:
        # 在线程池中执行同步的 Selenium 操作
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                _perform_weibo_login_sync,
                request.username,
                request.password
            ),
            timeout=120.0  # 120秒超时（2分钟）
        )

        if result['success']:
            # 登录成功，更新 .env 文件
            await _update_env_file(result['cookie'])

            return WeiboLoginResponse(
                success=True,
                cookie=result['cookie'],
                message=result['message'],
                error=None
            )
        else:
            return WeiboLoginResponse(
                success=False,
                cookie=None,
                message=result['message'],
                error=result.get('error')
            )

    except asyncio.TimeoutError:
        logger.error("❌ 登录超时")
        return WeiboLoginResponse(
            success=False,
            cookie=None,
            message="登录超时，请重试",
            error="Login timeout"
        )
    except Exception as e:
        logger.error(f"❌ 登录接口异常: {e}", exc_info=True)
        return WeiboLoginResponse(
            success=False,
            cookie=None,
            message=f"登录接口异常: {str(e)}",
            error=str(e)
        )


@router.get("/cookie-status")
async def get_cookie_status():
    """
    获取当前微博 Cookie 状态

    Returns:
        dict: Cookie 状态信息
    """
    from ..agent.config import get_settings

    settings = get_settings()
    has_cookie = bool(settings.weibo_cookie)

    return {
        "has_cookie": has_cookie,
        "cookie_length": len(settings.weibo_cookie) if has_cookie else 0,
        "cookie_preview": settings.weibo_cookie[:20] + "..." if has_cookie and len(settings.weibo_cookie) > 20 else None
    }


@router.post("/extract-cookie")
async def extract_cookie(request: dict):
    """
    从微博登录页面提取 Cookie
    
    由于跨域限制，前端无法直接从 iframe 中提取 Cookie
    这个端点返回一个说明，告诉用户如何手动获取 Cookie
    
    Args:
        request: 包含微博登录 URL 的请求
    
    Returns:
        dict: 提取结果
    """
    login_url = request.get("url", "https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.19)&entry=miniblog")
    
    logger.info(f"📥 收到 Cookie 提取请求: {login_url}")
    
    # 由于跨域限制，我们无法直接从 iframe 中提取 Cookie
    # 返回一个说明，告诉用户如何手动获取 Cookie
    return {
        "success": False,
        "cookie": None,
        "message": "由于浏览器跨域安全限制，无法直接从 iframe 中提取 Cookie。请按照以下步骤手动获取：\n\n1. 在上方登录页面完成微博登录\n2. 登录成功后，按 F12 打开浏览器开发者工具\n3. 切换到 'Application' 或 '存储' 标签\n4. 展开 'Cookies' → 'https://weibo.com'\n5. 找到名为 'SUB' 和 'SUBP' 的 Cookie 值\n6. 将两个 Cookie 值复制，格式为：SUB=xxx; SUBP=xxx\n7. 将复制的 Cookie 粘贴到下方的输入框中",
        "error": "Cross-origin restriction"
    }


@router.post("/manual-cookie")
async def manual_cookie(request: dict):
    """
    手动输入 Cookie
    
    Args:
        request: 包含 Cookie 值的请求
    
    Returns:
        dict: 保存结果
    """
    cookie = request.get("cookie", "")
    
    if not cookie:
        return {
            "success": False,
            "cookie": None,
            "message": "Cookie 不能为空",
            "error": "Empty cookie"
        }
    
    logger.info(f"📥 收到手动 Cookie 输入: {cookie[:50]}...")
    
    # 验证 Cookie 格式
    if 'SUB=' not in cookie:
        return {
            "success": False,
            "cookie": None,
            "message": "Cookie 格式不正确，必须包含 SUB 值",
            "error": "Invalid cookie format"
        }
    
    # 保存到 .env 文件
    success = await _update_env_file(cookie)
    
    if success:
        return {
            "success": True,
            "cookie": cookie,
            "message": "Cookie 保存成功",
            "error": None
        }
    else:
        return {
            "success": False,
            "cookie": None,
            "message": "Cookie 保存失败",
            "error": "Failed to save cookie"
        }
