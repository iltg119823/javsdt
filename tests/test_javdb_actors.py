from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from Functions.Web.Javdb import extract_actors, scrape_from_db
from Class.MyJav import JavFile, JavModel
from test_batch_control import make_config, working_directory
from test_javdb_search import SEARCH, DETAIL


class JavdbActorTests(unittest.TestCase):
    def test_whitespace_between_link_and_gender_marker(self):
        html = '<div><a href="/actors/example">三葉ちはる</a>\n  <strong class="symbol female">♀</strong></div>'
        self.assertEqual(extract_actors(etree.HTML(html)), ['三葉ちはる'])

    def test_nested_names_attributes_and_alternate_gender_element(self):
        html = '<div><a class="actor" href="/actors/example"><span>三葉ちはる</span></a><span class="female symbol">♀</span></div>'
        self.assertEqual(extract_actors(etree.HTML(html)), ['三葉ちはる'])

    def test_explicit_male_is_excluded_and_duplicate_names_deduplicated(self):
        html = '<div><a href="/actors/m">Male fixture</a> <strong class="symbol male">♂</strong><a href="/actors/f">Actress</a><a href="/actors/f">Actress</a></div>'
        self.assertEqual(extract_actors(etree.HTML(html)), ['Actress'])

    def test_missing_gender_marker_is_supported(self):
        self.assertEqual(extract_actors(etree.HTML('<a href="/actors/example">Actress</a>')), ['Actress'])

    def test_detail_scraper_stores_actor_names(self):
        detail = DETAIL.replace('<span>4.5 分</span>', '<a href="/actors/example">Actress</a>\n<strong class="symbol female">♀</strong><span>4.5 分</span>')
        file = JavFile('DLDSS-558', 'DLDSS-558', 'DLDSS-558.mp4', '.', 1, '', 1)
        model = JavModel()
        with patch('Functions.Web.Javdb.get_db_html', side_effect=[SEARCH, detail]):
            scrape_from_db(file, model, 'https://javdb.com', {})
        self.assertEqual(model.Actors, ['Actress'])

    def test_writer_outputs_actor_and_escapes_name(self):
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            handler = make_config()
            handler._bool_nfo = True
            file = JavFile('ABC-123', 'ABC-123', 'ABC-123.mp4', directory, 1, '', 1)
            model = JavModel(Car='ABC-123', Title='Fixture', Actors=['A & B'])
            handler.prefect_dict_for_standard(file, model)
            handler.write_nfo(file, model, [])
            movie = ElementTree.parse(Path(directory) / 'ABC-123.nfo').getroot()
            self.assertEqual(movie.findtext('actor/name'), 'A & B')


if __name__ == '__main__':
    unittest.main()
