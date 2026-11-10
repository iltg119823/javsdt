from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from Class.MyJav import JavFile, JavModel
from Class.MyEnum import ScrapeStatusEnum
from Class.MyError import SourceUnavailableError
from Functions.Web.Javdb import scrape_from_db
from Functions.Web.Javlibrary import get_library_html

# Synthetic structural fixtures; these are not live-captured pages.
SEARCH = '''<html><title>JavDB</title><div class="movie-list h cols-4">
<div class="item"><a href="/v/Other"><div class="video-title"><strong>DLDSS-543</strong></div></a></div>
<div class="item"><a href="/v/Exact"><div class="video-title"><strong>DLDSS-558</strong></div></a></div>
</div></html>'''
DETAIL = '''<html><title>DLDSS-558 Example title | JavDB</title>
<div class="video-meta-panel"><div class="panel-block"><strong>日期:</strong><span>2026-01-02</span></div>
<div class="panel-block"><span class="value">120 分鐘</span></div>
<a href="/series/abc">Example series</a><a href="/makers/abc">Example studio</a>
<a href="/directors/abc">Example director</a><a href="/tags/abc">Example genre</a>
<span>4.5 分</span></div></html>'''


class JavdbSearchTests(unittest.TestCase):
    def setUp(self):
        self.file = JavFile('DLDSS-558', 'DLDSS-558', '4k688.com@DLDSS-558.mp4', '.', 1, '', 1)
        self.model = JavModel()

    def test_complete_identifier_search_and_detail(self):
        with patch('Functions.Web.Javdb.get_db_html', side_effect=[SEARCH, DETAIL]) as get:
            status, genres = scrape_from_db(self.file, self.model, 'https://javdb.com', {})
        self.assertEqual(status, ScrapeStatusEnum.success)
        self.assertEqual(get.call_args_list[0].args[0], 'https://javdb.com/search?q=DLDSS-558&f=all')
        self.assertEqual(get.call_args_list[1].args[0], 'https://javdb.com/v/Exact')
        self.assertEqual(self.model.Car, 'DLDSS-558')
        self.assertEqual(self.model.Title, 'Example title')
        self.assertEqual(self.model.Release, '2026-01-02')
        self.assertEqual(self.model.Runtime, 120)
        self.assertEqual(self.model.Score, 90)
        self.assertEqual(genres, ['Example genre'])

    def test_similar_identifier_is_not_selected(self):
        with patch('Functions.Web.Javdb.get_db_html', return_value=SEARCH.replace('DLDSS-558', 'DLDSS-5580')) as get:
            status, _ = scrape_from_db(self.file, self.model, 'https://javdb.com', {})
        self.assertEqual(status, ScrapeStatusEnum.db_not_found)
        self.assertEqual(get.call_count, 1)
        self.assertEqual(self.model.Javdb, '')

    def test_challenge_page_is_not_treated_as_no_results(self):
        with patch('Functions.Web.Javdb.get_db_html', return_value='<title>JavDB login required</title>'):
            with self.assertRaises(SourceUnavailableError):
                scrape_from_db(self.file, self.model, 'https://javdb.com', {})

    def test_detail_identity_must_match(self):
        with patch('Functions.Web.Javdb.get_db_html', side_effect=[SEARCH, DETAIL.replace('DLDSS-558', 'DLDSS-543')]):
            with self.assertRaises(SourceUnavailableError):
                scrape_from_db(self.file, self.model, 'https://javdb.com', {})
        self.assertEqual(self.model.Javdb, '')

    def test_multiple_exact_results_are_not_selected_arbitrarily(self):
        search = SEARCH.replace('DLDSS-543', 'DLDSS-558')
        with patch('Functions.Web.Javdb.get_db_html', return_value=search):
            status, _ = scrape_from_db(self.file, self.model, 'https://javdb.com', {})
        self.assertEqual(status, ScrapeStatusEnum.db_multiple_search_results)

    def test_legacy_library_host_is_replaced_and_custom_mirror_preserved(self):
        for host, expected in [('www.n53i.com', 'www.javlibrary.com'), ('n53i.com', 'www.javlibrary.com'), ('mirror.example', 'mirror.example')]:
            with self.subTest(host=host), patch('Functions.Web.Javlibrary.get_html', return_value='JAVLibrary') as get:
                get_library_html(f'https://{host}/cn/vl_searchbyid.php?keyword=DLDSS-558', {})
                self.assertEqual(get.call_args.args[0], f'https://{expected}/cn/vl_searchbyid.php?keyword=DLDSS-558')


if __name__ == '__main__':
    unittest.main()
