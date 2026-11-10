from Functions.Web.Http import get_html
# -*- coding:utf-8 -*-
import re
from lxml import etree

# from traceback import format_exc

from Functions.Metadata.Car import extract_number_from_car_suf, extract_number_from_car
from Class.MyEnum import ScrapeStatusEnum
from Class.MyError import SpecifiedUrlError, SourceUnavailableError


# 请求jav在javdb上的网页，返回html
def get_db_html(url, proxy):
    return get_html(url, proxy, ('JavDB', '頁面未找到'), headers={'User-Agent': 'Mozilla/5.0'})


def scrape_from_db(jav_file, jav_model, url_db, proxy_db):
    # 用户指定了网址，则直接得到jav所在网址
    if '仓库' in jav_file.Name:
        url_appointg = re.search(r'仓库(\w+?)\.', jav_file.Name)
        if url_appointg:
            javdb = url_appointg.group(1)
            url_jav_db = f'{url_db}/v/{javdb}'
            html_jav_db = get_db_html(url_jav_db, proxy_db)
            if re.search(r'頁面未找到', html_jav_db):
                raise SpecifiedUrlError(f'你指定的javdb网址找不到jav: {url_jav_db}，')
        else:
            # 指定的javlibrary网址有错误
            raise SpecifiedUrlError(f'你指定的javdb网址有错误: ')

    # Search the complete identifier rather than estimating a prefix catalogue page.
    else:
        from urllib.parse import urlencode
        url_search = f'{url_db}/search?{urlencode({"q": jav_file.Car, "f": "all"})}'
        print('    >搜索javdb: ', url_search)
        html_search = get_db_html(url_search, proxy_db)
        tree = etree.HTML(html_search)
        if tree is None:
            raise SourceUnavailableError('JavDB 返回了无法解析的搜索页。')
        matches = []
        for link in tree.xpath('//a[contains(@href, "/v/")]'):
            codes = link.xpath('.//strong/text()')
            if any(normalize_car(code) in (normalize_car(jav_file.Car), normalize_car(jav_file.Car_id)) for code in codes):
                match = re.fullmatch(r'/v/([A-Za-z0-9]+)', link.get('href', ''))
                if match and match.group(1) not in matches:
                    matches.append(match.group(1))
        if not matches:
            # Only a recognized results layout establishes a genuine no-match result.
            if tree.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " movie-list ")]') or any(
                    marker in html_search for marker in ('沒有結果', '没有结果', 'No results')):
                return ScrapeStatusEnum.db_not_found, []
            raise SourceUnavailableError('JavDB 未返回可识别的搜索结果，可能需要验证、登录，或网站结构已变化。')
        if len(matches) > 1:
            return ScrapeStatusEnum.db_multiple_search_results, []
        javdb = matches[0]

    # 得到 javdb
    url_jav_db = f'{url_db}/v/{javdb}'
    print('    >前往javdb: ', url_jav_db)
    html_jav_db = get_db_html(url_jav_db, proxy_db)
    tree = etree.HTML(html_jav_db)
    if tree is None:
        raise SourceUnavailableError('JavDB 返回了无法解析的详情页。')
    title = ' '.join(tree.xpath('//title/text()')).strip()
    title = re.split(r'\s*[|｜]\s*JavDB', title, maxsplit=1)[0].strip()
    title_parts = title.split(None, 1)
    if len(title_parts) != 2 or normalize_car(title_parts[0]) not in (normalize_car(jav_file.Car), normalize_car(jav_file.Car_id)):
        raise SourceUnavailableError('JavDB 详情页番号不匹配或缺少标题，跳过该结果。')
    jav_model.Car, jav_model.Title = title_parts
    jav_model.Javdb = javdb
    # Scope metadata to the information panel when present; tolerate translated labels.
    panels = tree.xpath('//*[contains(concat(" ", normalize-space(@class), " "), " video-meta-panel ")]')
    if panels:
        html_jav_db = etree.tostring(panels[0], encoding='unicode', method='html')
    # 系列 "/series/RJmR">○○に欲望剥き出しでハメまくった中出し記録。</a>
    seriesg = re.search(r'series/.+?">(.+?)</a>', html_jav_db)
    jav_model.Series = seriesg.group(1) if seriesg else ''
    # 上映日 e">2019-02-01<
    releaseg = re.search(r'(\d\d\d\d-\d\d-\d\d)', html_jav_db)
    jav_model.Release = releaseg.group(1) if releaseg else '1970-01-01'
    # 片长 value">175 分鍾<
    runtimeg = re.search(r'value">\s*(\d+)\s*(?:分鍾|分鐘|分钟|minute)', html_jav_db)
    jav_model.Runtime = int(runtimeg.group(1)) if runtimeg else 0
    # 导演 /directors/WZg">NABE<
    directorg = re.search(r'directors/.+?">(.+?)<', html_jav_db)
    jav_model.Director = directorg.group(1) if directorg else ''
    # 制作商 e"><a href="/makers/
    studiog = re.search(r'makers/.+?">(.+?)<', html_jav_db)
    jav_model.Studio = studiog.group(1) if studiog else ''
    # 发行商 /publishers/pkAb">AV OPEN 2018</a><
    publisherg = re.search(r'publishers.+?">(.+?)</a><', html_jav_db)
    jav_model.Publisher = publisherg.group(1) if publisherg else ''
    # 评分 star gray"></i></span>&nbsp;3.75分
    scoreg = re.search(r'(?<![\d.])([0-5](?:\.\d+)?)\s*分(?![鐘鍾钟])', html_jav_db)
    jav_model.Score = int(float(scoreg.group(1)) * 20) if scoreg else 0
    # 演员们 /actors/M0xA">上川星空</a>  actors/P9mN">希美まゆ</a><strong class="symbol female
    actors = re.findall(r'actors/.+?">(.+?)</a><strong class="symbol female', html_jav_db)
    jav_model.Actors = [i.strip() for i in actors]
    str_actors = ' '.join(jav_model.Actors)
    # 去除末尾的标题 javdb上的演员不像javlibrary使用演员最熟知的名字
    if str_actors and jav_model.Title.endswith(str_actors):
        jav_model.Title = jav_model.Title[:-len(str_actors)].strip()
    # print('    >演员: ', actors)
    # 特征 /tags?c7=8">精选、综合</a>
    genres_db = re.findall(r'tags.+?">(.+?)</a>', html_jav_db)
    return ScrapeStatusEnum.success, genres_db


def find_javdb_code(suf_current, list_cars):
    for i, suf_str in enumerate(list_cars):
        if int(extract_number_from_car(suf_str)) == suf_current:
            return i + 1    # 第几个，在list的下标基础上+1
    return ''


def normalize_car(value):
    """Compare catalogue identifiers while tolerating separators and zero padding."""
    match = re.fullmatch(r'([A-Z]+|T28)[-_ ]*(\d+)', value.strip().upper())
    return (match.group(1), int(match.group(2))) if match else value.strip().upper()
