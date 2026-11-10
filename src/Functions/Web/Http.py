"""Bounded requests with actionable errors and no interactive prompts."""
from urllib.parse import urlsplit
import requests
from time import monotonic, sleep, time
from email.utils import parsedate_to_datetime
from html import unescape
import re
from Class.MyError import SourceUnavailableError

_failed_sources = {}
_failed_mirror = {}
_sessions = {}
_last_request = {}
MIN_REQUEST_INTERVAL = 3.0


def reset_sources():
    _failed_sources.clear()
    _failed_mirror.clear()
    _last_request.clear()
    for session in _sessions.values():
        session.close()
    _sessions.clear()


def _request(url, **kwargs):
    host = urlsplit(url).netloc
    session = _sessions.get(host)
    if session is None:
        session = _sessions[host] = requests.Session()
    return session.get(url, **kwargs)


def _pace(host):
    if host in _last_request:
        delay = MIN_REQUEST_INTERVAL - (monotonic() - _last_request[host])
        if delay > 0:
            sleep(delay)
    _last_request[host] = monotonic()


def _is_temporary_gate(html):
    # Specific page notices, not the normal login links in the site navigation.
    text = unescape(re.sub(r'<[^>]+>', ' ', html))
    text = re.sub(r'\s+', '', text).lower()
    return any(marker in text for marker in (
        '此内容需要登入才能查看或操作', '此內容需要登入才能查看或操作',
        '此内容需要登录才能查看或操作', '此內容需要登錄才能查看或操作',
    ))


def _refresh_delay(response):
    value = response.headers.get('Retry-After', '').strip()
    delay = 0.0
    if value:
        try:
            delay = float(value)
        except ValueError:
            try:
                delay = parsedate_to_datetime(value).timestamp() - time()
            except (ValueError, TypeError, OverflowError):
                pass
    # Do not send an early retry when the server asks for a long pause.
    return None if delay > 60 else max(10.0, delay)


def _wait_for_refresh(response, host):
    delay = _refresh_delay(response)
    if delay is None:
        print(f'    >{host} 要求较长等待，本轮暂停，请稍后再运行。')
        return False
    print(f'    >{host} 返回访问限制或临时提示页，保留会话等待 {delay:g} 秒后重试一次...')
    sleep(delay)
    return True


def get_html(url, proxy, markers, headers=None, retry_refresh=False):
    host = urlsplit(url).netloc
    if host in _failed_sources:
        raise SourceUnavailableError(f'{host} 本轮已暂停：{_failed_sources[host]}', allow_mirror=_failed_mirror.get(host, False))
    allow_mirror = False
    reason = '网页内容与预期不符（可能是地址失效、验证页面或网站结构变化）'
    for attempt in range(2):
        try:
            _pace(host)
            with _request(url, proxies=proxy or None, headers=headers,
                              timeout=(4, 8)) as response:
                response.raise_for_status()
                allow_mirror = False
                response.encoding = 'utf-8'
                html = response.text
                if _is_temporary_gate(html):
                    allow_mirror = False
                    reason = '返回登录提示页，尚未获得影片信息（不能据此判断必须登录）'
                    if retry_refresh and attempt == 0 and _wait_for_refresh(response, host):
                        continue
                    break
                if any(marker.lower() in html.lower() for marker in markers):
                    return html
                break
        except requests.exceptions.HTTPError as error:
            reason = f'HTTP {error.response.status_code}'
            allow_mirror = error.response.status_code in (500, 502, 503, 504)
            if retry_refresh and error.response.status_code == 403 and attempt == 0:
                if _wait_for_refresh(error.response, host):
                    continue
            if error.response.status_code in (502, 503, 504) and attempt == 0:
                print(f'    >访问 {host} 失败（{reason}），再尝试一次...')
                continue
            break
        except requests.exceptions.RequestException as error:
            reason = type(error).__name__
            allow_mirror = True
            if attempt == 0:
                print(f'    >访问 {host} 失败（{reason}），再尝试一次...')
    _failed_sources[host] = reason
    _failed_mirror[host] = allow_mirror
    raise SourceUnavailableError(f'{url}：{reason}。请检查配置中的站点地址和代理；本轮暂停该站点。', allow_mirror=allow_mirror)
