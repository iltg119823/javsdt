"""Bounded requests with actionable errors and no interactive prompts."""
from urllib.parse import urlsplit
import requests
from Class.MyError import SourceUnavailableError

_failed_sources = {}


def reset_sources():
    _failed_sources.clear()


def get_html(url, proxy, markers, headers=None):
    host = urlsplit(url).netloc
    if host in _failed_sources:
        raise SourceUnavailableError(f'{host} 本轮已暂停：{_failed_sources[host]}')
    reason = '网页内容与预期不符（可能是地址失效、验证页面或网站结构变化）'
    for attempt in range(2):
        try:
            with requests.get(url, proxies=proxy or None, headers=headers,
                              timeout=(4, 8)) as response:
                response.raise_for_status()
                response.encoding = 'utf-8'
                html = response.text
                if any(marker.lower() in html.lower() for marker in markers):
                    return html
                break
        except requests.exceptions.HTTPError as error:
            reason = f'HTTP {error.response.status_code}'
            if error.response.status_code in (502, 503, 504) and attempt == 0:
                print(f'    >访问 {host} 失败（{reason}），再尝试一次...')
                continue
            break
        except requests.exceptions.RequestException as error:
            reason = type(error).__name__
            if attempt == 0:
                print(f'    >访问 {host} 失败（{reason}），再尝试一次...')
    _failed_sources[host] = reason
    raise SourceUnavailableError(f'{url}：{reason}。请检查配置中的站点地址和代理；本轮暂停该站点。')
