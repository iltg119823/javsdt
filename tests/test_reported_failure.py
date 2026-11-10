from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from Class.MyError import SourceUnavailableError
from Class.MyJav import JavFile, JavModel
from Class.MyEnum import ScrapeStatusEnum
from Functions.Metadata.Car import find_car_youma
from Functions.Web.Http import get_html, reset_sources
from Functions.Progress.Prepare import get_suren_cars
import Youma


class ReportedFailureTests(unittest.TestCase):
    def setUp(self):
        reset_sources()

    def test_advertising_domains_do_not_become_identifiers(self):
        cases = {
            '4k688.com@DLDSS-558.mp4': 'DLDSS-558',
            'https://4k688.com@DLDSS-558.mp4': 'DLDSS-558',
            '[4k688.com]DLDSS-558.mp4': 'DLDSS-558',
            '4K688.COM@ABP00127-C.mp4': 'ABP-127',
            '4k688.com@T28-123.mp4': 'T28-123',
            '4k688.com@20ID-020.mp4': 'ID-20020',
            'DLDSS-558.mp4': 'DLDSS-558',
            'HEYZO-1234.mp4': '',
        }
        for filename, expected in cases.items():
            with self.subTest(filename=filename):
                self.assertEqual(find_car_youma(filename, get_suren_cars()), expected)

    def test_timeout_retries_twice_without_prompt_and_pauses_host(self):
        with patch('Functions.Web.Http.requests.get', side_effect=requests.Timeout) as get, patch('builtins.input') as prompt:
            with self.assertRaisesRegex(SourceUnavailableError, 'Timeout'):
                get_html('https://example.test/search', {}, ('JavDB',))
            self.assertEqual(get.call_count, 2)
            with patch('Functions.Web.Http.requests.get') as retry:
                with self.assertRaises(SourceUnavailableError):
                    get_html('https://example.test/second', {}, ('JavDB',))
                retry.assert_not_called()
            prompt.assert_not_called()

    def test_http_503_retries_once_and_reports_status(self):
        response = requests.Response()
        response.status_code = 503
        response.url = 'https://example.test/search'
        with patch('Functions.Web.Http.requests.get') as get:
            get.return_value.__enter__.return_value = response
            with self.assertRaisesRegex(SourceUnavailableError, 'HTTP 503'):
                get_html(response.url, {}, ('JavDB',))
            self.assertEqual(get.call_count, 2)

    def test_failed_source_does_not_leave_partial_metadata(self):
        model = JavModel(Title='existing title')
        def broken(file, candidate, url, proxy):
            candidate.Javdb = 'incomplete'
            candidate.Title = 'partial title'
            raise SourceUnavailableError('offline')
        status, genres = Youma.scrape_available(broken, Mock(), model, 'https://example.test', {}, Mock())
        self.assertEqual(status, ScrapeStatusEnum.interrupted)
        self.assertEqual(genres, [])
        self.assertEqual(model.Title, 'existing title')
        self.assertEqual(model.Javdb, '')

    def test_next_source_can_succeed_after_failure(self):
        model = JavModel()
        logger = Mock()
        failed = Mock(side_effect=SourceUnavailableError('offline'))
        def success(file, candidate, url, proxy):
            candidate.Javlibrary = 'example'
            candidate.Title = 'complete title'
            return ScrapeStatusEnum.success, ['genre']
        Youma.scrape_available(failed, Mock(), model, 'https://first.test', {}, logger)
        status, genres = Youma.scrape_available(success, Mock(), model, 'https://second.test', {}, logger)
        self.assertEqual((status, genres), (ScrapeStatusEnum.success, ['genre']))
        self.assertEqual(model.Title, 'complete title')

    def test_no_rename_or_move_when_primary_sources_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            video = Path(directory) / '4k688.com@DLDSS-558.mp4'
            video.write_bytes(b'fixture')
            jav_file = JavFile('DLDSS-558', 'DLDSS-558', video.name, directory, 1, '', 1)
            handler = Mock(to_language='zh')
            handler.get_list_jav_files.return_value = [jav_file]
            with patch.object(Youma, 'scrape_from_db', side_effect=SourceUnavailableError('db offline')), \
                    patch.object(Youma, 'scrape_from_library', side_effect=SourceUnavailableError('library offline')), \
                    patch.object(Youma, 'scrape_from_bus') as bus, \
                    patch.object(Youma, 'Logger'):
                Youma.Youma(directory, handler)
            handler.rename_mp4.assert_not_called()
            handler.classify_files.assert_not_called()
            handler.rename_folder.assert_not_called()
            handler.classify_folder.assert_not_called()
            bus.assert_not_called()
            self.assertEqual(video.read_bytes(), b'fixture')


if __name__ == '__main__':
    unittest.main()
