"""User-editable JavDB site settings, separate from the existing organizing INI."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit, urlunsplit

SETTINGS_FILE = 'JavDB-Sites.json'
DEFAULT_PRIMARY = 'https://javdb.com'
DEFAULT_BACKUP = 'https://javdb580.com'


def validate_sites(primary, backups):
    if not isinstance(primary, str) or not isinstance(backups, list):
        raise ValueError('主站必须是网址，备用站必须是网址列表')
    result = []
    for address in [primary] + backups:
        if not isinstance(address, str):
            raise ValueError('站点网址必须是文字')
        address = address.strip()
        if not address:
            continue
        if any(character.isspace() for character in address):
            raise ValueError('站点网址中不能包含空格或换行')
        parts = urlsplit(address)
        if parts.scheme not in ('https', 'http') or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ('', '/'):
            raise ValueError('请输入完整 HTTP/HTTPS 站点地址，不要填写账号、查询参数或影片详情链接')
        try:
            parts.port
        except ValueError:
            raise ValueError('站点端口无效')
        clean = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip('/'), '', ''))
        if clean not in result:
            result.append(clean)
    if not primary.strip() or not result:
        raise ValueError('请填写主站地址')
    if len(result) > 5:
        raise ValueError('最多设置 5 个站点')
    return result


def load_sites(primary=DEFAULT_PRIMARY, path=SETTINGS_FILE):
    path = Path(path)
    if path.exists():
        settings = json.loads(path.read_text(encoding='utf-8-sig'))
        return validate_sites(settings['primary'], settings.get('backups', []))
    return validate_sites(primary, [DEFAULT_BACKUP])


def save_sites(primary, backups, path=SETTINGS_FILE):
    sites = validate_sites(primary, backups)
    target = Path(path)
    temporary = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.resolve().parent,
                                suffix='.tmp', delete=False) as stream:
            temporary = stream.name
            json.dump({'primary': sites[0], 'backups': sites[1:]}, stream, ensure_ascii=False, indent=2)
        os.replace(temporary, target)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return sites
