"""Repair actor fields in existing NFOs without touching videos or artwork."""
import json
import os
from pathlib import Path
import re
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree

from Class.MyHandler import Handler
from Class.MyJav import JavFile, JavModel
from Class.MyEnum import ScrapeStatusEnum
from Class.MyError import SourceUnavailableError
from Functions.Metadata.Actor import normalize_actors
from Functions.Progress.User import choose_directory
from Functions.Utils.JsonUtility import save_metadata
from Functions.Web.Http import reset_sources
from Functions.Web.Javdb import scrape_from_db


def patch_nfo(path, names, aliases=None):
    names = normalize_actors(names)
    if not names:
        return False
    path = Path(path)
    original = path.read_bytes()
    text = original.decode('utf-8-sig')
    root = ElementTree.fromstring(text)
    if root.tag != 'movie':
        raise ValueError('NFO 根节点不是 movie')
    old = [actor.findtext('name', '') for actor in root.findall('actor')]
    if old == names:
        return False
    # Preserve all unrelated metadata and original text formatting.
    text = re.sub(r'<actor\b[^>]*>[\s\S]*?</actor\s*>', '', text)
    text = re.sub(r'<actor\b[^>]*/\s*>', '', text)
    if text.count('</movie>') != 1:
        raise ValueError('NFO 缺少唯一的 movie 闭合标签')
    existing = {}
    for actor in root.findall('actor'):
        canonical = normalize_actors([actor.findtext('name', '')], aliases)
        if canonical:
            existing.setdefault(canonical[0], actor)
    blocks = []
    for name in names:
        actor = existing.get(name)
        if actor is None:
            actor = ElementTree.Element('actor')
        name_node = actor.find('name')
        if name_node is None:
            name_node = ElementTree.SubElement(actor, 'name')
        name_node.text = name
        if actor.find('type') is None:
            ElementTree.SubElement(actor, 'type').text = 'Actor'
        actor.tail = None
        blocks.append('  ' + ElementTree.tostring(actor, encoding='unicode') + '\n')
    actors = ''.join(blocks)
    updated = text.replace('</movie>', actors + '</movie>')
    ElementTree.fromstring(updated)
    backup = path.with_name(path.name + '.before-actors.bak')
    if not backup.exists():
        # Exclusive creation preserves the first backup, including on repeat runs.
        with backup.open('xb') as stream:
            stream.write(original)
    temporary = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                suffix='.tmp', delete=False) as stream:
            temporary = stream.name
            stream.write(updated)
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    return True


def repair_directory(directory, handler, cache_root, aliases=None, scrape=scrape_from_db):
    reset_sources()
    cache_root = Path(cache_root)
    stats = {'updated': 0, 'unchanged': 0, 'missing': 0, 'errors': 0, 'pending': 0}
    paths = sorted(Path(directory).rglob('*.nfo'))
    checked = {}
    for index, path in enumerate(paths):
        print(f'[{index + 1}/{len(paths)}] {path.name}')
        try:
            root = ElementTree.fromstring(path.read_text(encoding='utf-8-sig'))
            if root.tag != 'movie':
                raise ValueError('NFO 根节点不是 movie')
            current = normalize_actors([actor.findtext('name', '') for actor in root.findall('actor')], aliases)
            if current:
                changed = patch_nfo(path, current, aliases)
            else:
                car = (root.findtext('id') or root.findtext('num') or '').strip().upper()
                if not re.fullmatch(r'(?:[A-Z]+|T28)-\d+', car):
                    raise ValueError('NFO 番号无法确认，未修改')
                cache = cache_root / car.split('-')[0] / (car + '.json')
                if car not in checked:
                    model = JavModel()
                    if cache.exists():
                        entries = json.loads(cache.read_text(encoding='utf-8'))
                        if entries.get('Car', '').upper() == car:
                            model = JavModel(**entries)
                    names = normalize_actors(model.Actors, aliases)
                    if not names:
                        file = JavFile(car, car, path.stem + '.mp4', str(path.parent), 1, '', 1)
                        if model.Javdb and re.fullmatch(r'[A-Za-z0-9]+', model.Javdb):
                            file.Name = '仓库' + model.Javdb + '.mp4'
                        candidate = JavModel()
                        status, _ = scrape(file, candidate, handler.url_db, handler.proxy_db)
                        if status == ScrapeStatusEnum.success:
                            names = normalize_actors(candidate.Actors, aliases)
                            if names:
                                # Preserve cached titles, plots and other existing metadata.
                                if not model.Car or not model.Title:
                                    model = candidate
                                model.Actors = names
                                save_metadata(cache, model)
                    checked[car] = names
                names = checked[car]
                if not names:
                    stats['missing'] += 1
                    print('    >来源未提供演员，保留原 NFO。')
                    continue
                changed = patch_nfo(path, names)
            stats['updated' if changed else 'unchanged'] += 1
            print('    >演员已更新（原文件已备份）' if changed else '    >已有演员，无需修改。')
        except SourceUnavailableError as error:
            stats['pending'] = len(paths) - index
            print(f'    >{error}\n本轮暂停，当前及剩余 {stats["pending"]} 份 NFO 待处理。')
            break
        except (OSError, ValueError, TypeError, ElementTree.ParseError) as error:
            stats['errors'] += 1
            print(f'    >未修改：{error}')
    print(f'演员补全结束：{stats}')
    return stats


def main(args=None):
    args = args or []
    directory = args[0] if args else choose_directory()
    if not directory or not Path(directory).is_dir():
        print('请选择有效的影片文件夹。')
        return 1
    aliases_path = Path('演员别名.json')
    aliases = json.loads(aliases_path.read_text(encoding='utf-8-sig')) if aliases_path.exists() else {}
    if not isinstance(aliases, dict):
        raise ValueError('演员别名.json 必须是名字到名字的 JSON 对象')
    handler = Handler('有码')
    cache = Path.cwd().parent / '【重要须备份】已整理的jsons'
    stats = repair_directory(directory, handler, cache, aliases)
    return 2 if stats['pending'] else (1 if stats['errors'] else 0)
