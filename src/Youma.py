# -*- coding:utf-8 -*-
import os
import sys
import json
from copy import deepcopy
from os.path import join
from shutil import move
from traceback import format_exc

from Class.MyHandler import Handler
from Class.MyEnum import ScrapeStatusEnum
from Class.MyLogger import Logger
from Class.MyJav import JavModel
from Class.MyError import TooManyDirectoryLevelsError, SpecifiedUrlError, SourceUnavailableError
from Functions.Web.Http import reset_sources
from Functions.Progress.User import choose_directory
from Functions.Metadata.Genre import better_dict_youma_genres
from Functions.Web.Javdb import scrape_from_db
from Functions.Web.Javlibrary import scrape_from_library
from Functions.Web.Javbus import scrape_from_bus
from Functions.Web.Arzon import scrape_from_arzon
from Functions.Utils.JsonUtility import read_json_to_dict, save_metadata
from urllib.parse import urlsplit

from Functions.Progress.Prepare import get_suren_cars
from Functions.Metadata.Car import find_car_youma


def scrape_available(scraper, jav_file, jav_model, url, proxy, logger):
    # Commit metadata only after a complete, successful source response.
    candidate = deepcopy(jav_model)
    try:
        status, genres = scraper(jav_file, candidate, url, proxy)
    except SourceUnavailableError as error:
        host = urlsplit(url).netloc
        warned = logger.__dict__.setdefault('_paused_source_warnings', set())
        if host not in warned:
            warned.add(host)
            logger.record_warn(str(error))
        return ScrapeStatusEnum.interrupted, []
    if status == ScrapeStatusEnum.success:
        jav_model.__dict__.update(candidate.__dict__)
    return status, genres


def CopyVideoOut(Path):
    validExt = [".mp4", ".mkv", ".avi"]
    buildPath = join(Path, "Build")
    if os.path.exists(buildPath) is False:
        os.makedirs(buildPath)

    list_suren_car = get_suren_cars()
    for root, _, files in os.walk(Path):
        if root == Path:
            continue
        if root == buildPath:
            continue
        for filename in files:
            if filename[-4:].lower() not in validExt:
                continue
            car = find_car_youma(filename.upper(), list_suren_car)
            if car == '':
                continue
            print(f"move({join(root, filename)}, {join(Path, filename)})")
            move(join(root, filename), join(buildPath, filename))
    return buildPath


def CopyVideoInside(Path):
    dirs = os.listdir(Path)
    # print(dirs)
    for root, _, files in os.walk(Path):
        # print(len(files))
        for fname in files:
            # print(fname)
            if fname[-5:] != ".part":
                continue
            sufix = fname[:-9]
            if sufix not in dirs:
                continue
            print(f"move({join(root, fname)}, {join(Path, sufix, fname)})")
            move(join(root, fname), join(Path, sufix, fname))


def ReadConfig():
    # region（1）读取配置
    print('正在读取ini中的设置...', end='')
    try:
        handler = Handler('有码')
    except:
        handler = None
        print(format_exc())
        input('\n无法读取ini文件，请修改它为正确格式，或者打开“【ini】重新创建ini.exe”创建全新的ini！')
    print('\n读取ini文件成功!\n')
    return handler
    # endregion


def Youma(dir_choose, handler):
    reset_sources()
    #  main开始
    # region（2）准备全局参数
    # 路径分隔符: 当前系统的路径分隔符 windows是“\”，linux和mac是“/”
    sep = os.sep
    # 当前程序文件夹 所处的 父文件夹路径
    dir_pwd_father = os.path.dirname(os.getcwd())
    # arzon通行证: 如果需要从arzon获取日语简介，需要先获得合法的arzon网站的cookie，用于通过成人验证。
    # 优化特征的字典
    dict_db_genres, _, _ = better_dict_youma_genres(
        handler.to_language)
    # 用于记录失败次数、失败信息
    logger = Logger()
    # endregion

    # region（3）整理程序
    # 用户输入“回车”就继续选择文件夹整理
    input_key = ''
    completed_skipped = 0
    while not input_key:

        # region （3.1）准备工作，用户选择需整理的文件夹，校验归类的目标文件夹的合法性
        logger.rest()
        # 用户选择需要整理的文件夹
        # 在txt中记录一下用户的这次操作，在某个时间选择了某个文件夹
        logger.record_start(dir_choose)
        # 新的所选文件夹，重置一些属性
        handler.rest_choose_dir(dir_choose)
        # endregion

        # region （3.2）遍历所选文件夹内部进行处理
        print('...文件扫描开始...如果时间过长...请避开高峰期...\n')
        # dir_current【当前所处文件夹】，由浅及深遍历每一层文件夹，list_sub_dirs【子文件夹们】 list_sub_files【子文件们】
        for dir_current, list_sub_dirs, list_sub_files in os.walk(dir_choose):
            # 新的一层级文件夹，重置一些属性
            handler.rest_current_dir(dir_current)
            # region （3.2.1）当前文件夹内包含jav及字幕文件的状况: 有多少视频，其中多少jav，同一车牌多少cd，当前文件夹是不是独立文件夹
            # （3.2.1.1）什么文件都没有 | 当前目录是之前已归类的目录，无需处理 | 判断这一层文件夹中有没有nfo
            if not list_sub_files \
                    or '归类完成' in dir_current[len(dir_choose):]:
                # or handler.judge_skip_exist_nfo(list_sub_files):
                continue  # dir_current[len(dir_choose):] 当前所处文件夹 相对于 所选文件夹 的路径，主要用于报错

            # （3.2.1.2）判断文件是不是字幕文件，放入dict_subtitle_file中，字幕文件和车牌对应关系 {'c:\a\abc_123.srt': 'abc-123'}
            handler.init_dict_subtitle_file(list_sub_files)
            # （3.2.1.3）获取当前所处文件夹，子一级内，包含的jav，放入list_jav_files 存放: 需要整理的jav文件对象jav_file;
            list_jav_files = handler.get_list_jav_files(list_sub_files)
            # （3.2.1.4）没有jav，则跳出当前所处文件夹
            if not list_jav_files:
                continue
            # （3.2.1.5）判定当前所处文件夹是否是独立文件夹，独立文件夹是指该文件夹仅用来存放该影片，而不是大杂烩文件夹，是后期移动剪切操作的重要依据
            # 错误：JavFile.Bool_in_separate_folder = handler.judge_separate_folder(len(list_jav_files), list_sub_dirs)
            # 我在主程序里修改JavFile.Bool_in_separate_folder并不会成功，你知道为什么吗？
            # handler.judge_separate_folder(len(list_jav_files), list_sub_dirs)
            # Bool_in_separate_folder是类属性，不是实例属性，修改类属性会将list_jav_files中的所有jav_file的Bool_in_separate_folder同步
            # （3.2.1.6）处理“集”的问题，（1）所选文件夹总共有多少个视频文件，包括非jav文件，主要用于显示进度（2）同一车牌有多少cd，用于cd2...命名
            handler.count_num_and_no(list_jav_files)
            # endregion

            # region（3.2.2）开始处理每一部jav文件
            for file_index, jav_file in enumerate(list_jav_files):
                try:
                    # region（3.2.2.1）准备工作
                    # 当前进度
                    print(
                        f'>> [{jav_file.No}/{handler.sum_videos_in_choose_dir}]:{jav_file.Name}'
                    )
                    print(f'    >发现车牌: {jav_file.Car}')
                    if handler.is_already_organized(jav_file) is True:
                        print('    >已有匹配的NFO及所需图片，跳过已完成影片，不请求网站。')
                        completed_skipped += 1
                        continue
                    logger.path_relative = jav_file.Path[len(
                        dir_choose):]  # 影片的相对于所选文件夹的路径，用于报错
                    # endregion

                    dir_prefs_jsons = f'{dir_pwd_father}{sep}【重要须备份】已整理的jsons{sep}{jav_file.Pref}{sep}'
                    path_json = f'{dir_prefs_jsons}{jav_file.Car}.json'
                    if os.path.exists(path_json):
                        print(f'    >从本地json读取元数据: {path_json}')
                        jav_model = JavModel(**read_json_to_dict(path_json))
                        genres = jav_model.Genres
                    else:
                        jav_model = JavModel()
                        # region（3.2.2.2）从javdb获取信息
                        status, genres_db = scrape_available(
                            scrape_from_db, jav_file, jav_model, handler.url_db,
                            handler.proxy_db, logger)
                        status_db = status
                        if status == ScrapeStatusEnum.db_not_found:
                            logger.record_warn(
                                f'javdb找不到该车牌的信息: {jav_file.Car}，')
                        # 优化genres_db
                        genres_db = [
                            dict_db_genres.get(i, i) for i in genres_db
                            if dict_db_genres.get(i, i) != '删除'
                        ]
                        # endregion

                        if not jav_model.Javdb:
                            if status_db == ScrapeStatusEnum.interrupted:
                                pending = list_jav_files[file_index:]
                                with open('【可删除】待处理记录.txt', 'a', encoding='utf-8') as stream:
                                    stream.write(f'JavDB 不可用，本轮暂停。所选目录：{dir_choose}\n')
                                    for item in pending:
                                        stream.write(f'{item.Car}\t{item.Path}\n')
                                    stream.write('其余子目录尚未继续扫描。\n\n')
                                print(f'JavDB 暂不可用，本轮暂停；当前目录 {len(pending)} 个文件待处理，其余子目录尚未继续扫描。')
                                return 2
                            logger.record_fail(f'JavDB 搜索未能唯一匹配该车牌: {jav_file.Car}，')
                            continue
                        genres = list(dict.fromkeys(genres_db))
                        jav_model.Genres = list(genres)

                        # 完善jav_model.CompletionStatus
                        jav_model.prefect_completion_status()

                    # region（3.2.3）后续完善
                    # Cache successful metadata even when translation is not configured.
                    handler.prefect_zh(jav_model)
                    save_metadata(path_json, jav_model)
                    print(f'    >保存本地json成功: {path_json}')

                    # 完善jav_file
                    handler.judge_subtitle_and_divulge(jav_file)
                    # 完善写入nfo中的genres
                    if jav_file.Bool_subtitle:  # 有“中字“，加上特征”中文字幕”
                        genres.append('中文字幕')
                    if jav_file.Bool_divulge:  # 是流出无码片，加上特征'无码流出'
                        genres.append('无码流出')

                    # 完善handler.dict_for_standard
                    handler.prefect_dict_for_standard(jav_file, jav_model)
                    # endregion

                    # 1重命名视频
                    path_new = handler.rename_mp4(jav_file)
                    if path_new:
                        logger.record_fail(f'请自行重命名大小写: ', path_new)

                    # 2 归类影片，只针对视频文件和字幕文件。注意: 第2操作和下面（第3操作+第7操作）互斥，只能执行第2操作或（第3操作+第7操作）
                    handler.classify_files(jav_file)

                    # 3重命名文件夹。如果是针对“文件”归类（即第2步），这一步会被跳过，因为用户只需要归类视频文件，不需要管文件夹。
                    handler.rename_folder(jav_file)

                    # 更新一下path_relative
                    logger.path_relative = f'{sep}{jav_file.Path.replace(dir_choose, "")}'  # 影片的相对于所选文件夹的路径，用于报错

                    # 4写入nfo【独特】
                    handler.write_nfo(jav_file, jav_model, genres)

                    # 5需要两张封面图片【独特】
                    handler.download_fanart(jav_file, jav_model)

                    # 6收集演员头像【相同】
                    handler.collect_sculpture(jav_file, jav_model)

                    # 7归类影片，针对文件夹【相同】
                    handler.classify_folder(jav_file)

                except SpecifiedUrlError as error:
                    logger.record_fail(str(error))
                    continue
                except KeyError as error:
                    logger.record_fail(f'发现新的特征需要添加至【特征对照表】，请告知作者: {error}，')
                    continue
                except FileExistsError as error:
                    logger.record_fail(str(error))
                    continue
                except TooManyDirectoryLevelsError as error:
                    logger.record_fail(str(error))
                    continue
                except:
                    logger.record_fail(
                        f'发生错误，如一直在该影片报错请截图并联系作者: {format_exc()}')
                    continue  # 【退出对该jav的整理】
            # endregion
        # endregion

        # 当前所选文件夹完成
        print('\n当前文件夹完成，', end='')
        logger.print_end(dir_choose)
        print(f'已跳过 {completed_skipped} 个已完成文件。')
        # input_key = input('回车继续选择文件夹整理: ')
        input_key = "False"
    # endregion


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    dir_choosed = args[0] if args else choose_directory()
    if not dir_choosed or not os.path.isdir(dir_choosed):
        print('请选择有效的影片文件夹。')
        return 1
    youma_handler = ReadConfig()
    if youma_handler is None:
        return 1
    result = Youma(dir_choosed, youma_handler)
    return result if isinstance(result, int) else 0


if __name__ == "__main__":
    sys.exit(main())
