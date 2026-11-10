import configparser
from contextlib import contextmanager
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from Class.MyHandler import Handler
from Class.MyJav import JavModel
from Class.MyError import SourceUnavailableError
from Class.MyEnum import ScrapeStatusEnum
from Functions.Utils.JsonUtility import save_metadata, read_json_to_dict
from Functions.Web import Http
import Youma


@contextmanager
def working_directory(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def make_config():
    with patch('builtins.input', return_value=''):
        runpy.run_path(str(ROOT / 'src/CreateIni.py'))
    config = configparser.RawConfigParser()
    config.read('【点我设置整理规则】.ini', encoding='utf-8-sig')
    for section, option in [('重命名视频文件', '是否重命名视频文件？'),
                            ('修改文件夹', '是否重命名或创建独立文件夹？'),
                            ('下载封面', '是否下载封面海报？'),
                            ('收集nfo', '是否收集nfo？')]:
        config.set(section, option, '否')
    with open('【点我设置整理规则】.ini', 'w', encoding='utf-8-sig') as stream:
        config.write(stream)
    return Handler('有码')


class BatchControlTests(unittest.TestCase):
    def tearDown(self):
        Http.reset_sources()

    def test_session_is_reused_and_closed_on_reset(self):
        Http.reset_sources()
        with patch.object(Http.requests, 'Session') as factory:
            Http._request('https://example.test/first')
            Http._request('https://example.test/second')
            factory.assert_called_once()
            self.assertEqual(factory.return_value.get.call_count, 2)
            Http.reset_sources()
            factory.return_value.close.assert_called_once()

    def test_requests_are_spaced_per_host(self):
        Http.reset_sources()
        Http._last_request['example.test'] = 100
        with patch.object(Http, 'monotonic', side_effect=[101, 103]), patch.object(Http, 'sleep') as sleep:
            Http._pace('example.test')
        sleep.assert_called_once_with(2)
        self.assertEqual(Http._last_request['example.test'], 103)

    def test_metadata_saved_without_translation_and_reused_for_segments(self):
        with tempfile.TemporaryDirectory() as base:
            program = Path(base) / 'program'
            program.mkdir()
            videos = Path(base) / 'videos'
            videos.mkdir()
            for part in (1, 2):
                (videos / f'VRKM-957-{part}.mp4').write_bytes(b'fixture')
            def scrape(file, candidate, url, proxy):
                candidate.Car = 'VRKM-957'
                candidate.Title = 'Fixture title'
                candidate.Javdb = 'Fixture'
                return ScrapeStatusEnum.success, []
            with working_directory(program):
                handler = make_config()
                with patch.object(Youma, 'scrape_from_db', side_effect=scrape) as db, \
                        patch.object(Youma, 'scrape_from_library', return_value=(ScrapeStatusEnum.library_not_found, [])), \
                        patch.object(Youma, 'scrape_from_bus', return_value=(ScrapeStatusEnum.bus_not_found, [])), \
                        patch.object(Youma, 'scrape_from_arzon', return_value=(ScrapeStatusEnum.arzon_not_found, {})):
                    Youma.Youma(str(videos), handler)
                self.assertEqual(db.call_count, 1)
            cache = Path(base) / '【重要须备份】已整理的jsons/VRKM/VRKM-957.json'
            self.assertEqual(read_json_to_dict(cache)['Title'], 'Fixture title')

    def test_blocked_batch_stops_after_first_file_and_records_pending(self):
        with tempfile.TemporaryDirectory() as base:
            program = Path(base) / 'program'
            program.mkdir()
            videos = Path(base) / 'videos'
            videos.mkdir()
            originals = [videos / f'ABC-{number}.mp4' for number in (123, 124, 125)]
            for path in originals:
                path.write_bytes(b'fixture')
            with working_directory(program):
                handler = make_config()
                with patch.object(Youma, 'scrape_from_db', side_effect=SourceUnavailableError('HTTP 403')) as db, \
                        patch.object(Youma, 'scrape_from_library', side_effect=SourceUnavailableError('HTTP 403')) as library, \
                        patch.object(Youma, 'scrape_from_bus') as bus:
                    result = Youma.Youma(str(videos), handler)
                self.assertEqual(result, 2)
                self.assertEqual(db.call_count, 1)
                self.assertEqual(library.call_count, 1)
                bus.assert_not_called()
                pending = Path('【可删除】待处理记录.txt').read_text(encoding='utf-8')
                self.assertTrue(all(str(path) in pending for path in originals))
                self.assertNotIn('失败！', Path('【可删除】失败记录.txt').read_text(encoding='utf-8'))
                self.assertTrue(all(path.read_bytes() == b'fixture' for path in originals))

    def test_failed_cache_replace_preserves_previous_metadata(self):
        with tempfile.TemporaryDirectory() as base:
            path = Path(base) / 'ABC/ABC-123.json'
            save_metadata(path, JavModel(Car='ABC-123', Title='old'))
            with patch('Functions.Utils.JsonUtility.os.replace', side_effect=OSError('disk error')):
                with self.assertRaises(OSError):
                    save_metadata(path, JavModel(Car='ABC-123', Title='new'))
            self.assertEqual(read_json_to_dict(path)['Title'], 'old')
            self.assertEqual(list(path.parent.glob('*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
