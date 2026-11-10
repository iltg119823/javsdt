"""Recognize complete local sidecars before requesting remote metadata."""
from pathlib import Path
from xml.etree import ElementTree
from PIL import Image


def is_complete(jav_file, need_images, fanart_formula, poster_formula, cd_only=False):
    stem = jav_file.Name_no_ext
    if cd_only and jav_file.Cd:
        stem = stem.replace(jav_file.Cd, '')
    nfo = Path(jav_file.Dir) / (stem + '.nfo')
    try:
        text = nfo.read_text(encoding='utf-8-sig')
        movie = ElementTree.fromstring(text)
        if movie.tag != 'movie' or not movie.findtext('title', '').strip():
            return False
        if movie.findtext('id', '').strip().upper() not in (jav_file.Car.upper(), jav_file.Car_id.upper()):
            return False
        if not need_images:
            return True
        values = {'视频': jav_file.Name_no_ext, '车牌': jav_file.Car, '空格': ' '}
        # Metadata-dependent custom image names cannot be safely inferred here.
        metadata_tokens = {'标题', '完整标题', '中文标题', '中文完整标题', '首个演员',
                           '全部演员', '系列', '片商', '发行年份', '发行月份', '发行日期',
                           '是否中字', '是否流出', '车牌前缀', '视频类型'}
        for formula in (fanart_formula, poster_formula):
            if any(token in metadata_tokens for token in formula):
                return False
            name = ''.join(values.get(token, token) for token in formula)
            if cd_only and jav_file.Cd:
                name = name.replace(jav_file.Cd, '')
            with Image.open(Path(jav_file.Dir) / name) as image:
                image.verify()
        return True
    except (OSError, ElementTree.ParseError, ValueError):
        return False
