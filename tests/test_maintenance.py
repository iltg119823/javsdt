import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import Mock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


class MaintenanceTests(unittest.TestCase):
    def test_import_entrypoint(self):
        import Youma

    def test_entrypoint_scans_selected_directory_without_pre_move(self):
        import Youma
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / 'ABC-123.mp4'
            video.write_bytes(b'test fixture')
            handler = Mock()
            with patch.object(Youma, 'ReadConfig', return_value=handler), \
                    patch.object(Youma, 'Youma') as organize, \
                    patch.object(Youma, 'CopyVideoOut') as move:
                self.assertEqual(Youma.main([directory]), 0)
                organize.assert_called_once_with(directory, handler)
                move.assert_not_called()
            self.assertTrue(video.exists())
            self.assertFalse((Path(directory) / 'Build').exists())

    def test_cancelled_directory_does_not_start(self):
        import Youma
        with patch.object(Youma, 'choose_directory', return_value=''), \
                patch.object(Youma, 'ReadConfig') as read:
            self.assertEqual(Youma.main([]), 1)
            read.assert_not_called()

    def test_javdb_proxy_request(self):
        from Functions.Web.Javdb import get_db_html
        response = MagicMock(text='JavDB 成人影片數據庫')
        response.__enter__.return_value = response
        proxy = {'https': 'http://localhost:8080'}
        with patch('Functions.Web.Javdb.requests.get', return_value=response) as get:
            self.assertEqual(get_db_html('https://example.test', proxy), response.text)
        self.assertEqual(get.call_args.kwargs['proxies'], proxy)
        self.assertIn('headers', get.call_args.kwargs)
        self.assertNotIn('header', get.call_args.kwargs)

    def test_generated_proxy_config(self):
        from configparser import RawConfigParser
        from Class.MyHandler import Handler
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            try:
                os.chdir(directory)
                with patch('builtins.input', return_value=''):
                    runpy.run_path(str(ROOT / 'src/CreateIni.py'))
                config = RawConfigParser()
                config.read('【点我设置整理规则】.ini', encoding='utf-8-sig')
                config.set('局部代理', '是否使用局部代理？', '是')
                config.set('局部代理', '是否代理javdb？', '是')
                for scheme, expected in [('http', 'http'), ('是', 'http'), ('socks5', 'socks5')]:
                    config.set('局部代理', 'http还是socks5？', scheme)
                    with open('【点我设置整理规则】.ini', 'w', encoding='utf-8-sig') as stream:
                        config.write(stream)
                    self.assertEqual(Handler('有码').proxy_db['https'], expected + '://127.0.0.1:10809')
            finally:
                os.chdir(previous)

    def test_real_excel_from_arbitrary_directory(self):
        from Functions.Metadata.Genre import better_dict_youma_genres
        for language in ('zh', 'cht'):
            dictionaries = better_dict_youma_genres(language)
            self.assertTrue(all(dictionaries))
            self.assertTrue(all(isinstance(v, str) for d in dictionaries for v in d.values()))

    def test_watermarks_with_current_pillow(self):
        from PIL import Image
        from Functions.Progress.Picture import add_watermark_subtitle, add_watermark_divulge
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as directory:
            poster = Path(directory) / 'poster.jpg'
            Image.new('RGB', (379, 538), 'white').save(poster)
            try:
                os.chdir(ROOT / 'src')
                add_watermark_subtitle(poster)
                add_watermark_divulge(poster)
                with Image.open(poster) as img:
                    self.assertEqual(img.size, (379, 538))
            finally:
                os.chdir(previous)


if __name__ == '__main__':
    unittest.main()
