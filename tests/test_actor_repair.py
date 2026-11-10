import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from ActorRepair import patch_nfo, repair_directory
from Functions.Metadata.Actor import normalize_actors
from Class.MyEnum import ScrapeStatusEnum
from Class.MyError import SourceUnavailableError


class ActorRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cache = self.root / 'cache'
        self.videos = self.root / 'videos'
        self.videos.mkdir()
        self.handler = Mock(url_db='https://example.test', proxy_db={})

    def nfo(self, name='ABC-123-part1', car='ABC-123', actors=''):
        path = self.videos / (name + '.nfo')
        path.write_text(f'<movie><title>Original title</title><id>{car}</id><plot>Keep my plot</plot>{actors}</movie>', encoding='utf-8')
        return path

    def cached(self, actors):
        path = self.cache / 'ABC/ABC-123.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({'Car': 'ABC-123', 'Title': 'Original title', 'Actors': actors, 'Javdb': 'KnownCode'}))
        return path

    def test_normalization_and_explicit_aliases(self):
        self.assertEqual(normalize_actors([' Ａ  Name ', 'A Name', 'Alias'], {'Alias': 'A Name'}), ['A Name'])
        self.assertEqual(normalize_actors(['別名', '本名']), ['別名', '本名'])
        self.assertEqual(normalize_actors('Single name'), ['Single name'])
        self.assertEqual(normalize_actors(None), [])

    def test_patch_only_actors_and_preserve_first_backup(self):
        path = self.nfo()
        original = path.read_bytes()
        self.assertTrue(patch_nfo(path, ['A & B', 'A & B']))
        movie = ElementTree.parse(path).getroot()
        self.assertEqual(movie.findtext('title'), 'Original title')
        self.assertEqual(movie.findtext('plot'), 'Keep my plot')
        self.assertEqual(movie.findtext('actor/name'), 'A & B')
        self.assertEqual(len(movie.findall('actor')), 1)
        self.assertFalse(patch_nfo(path, ['A & B']))
        self.assertEqual(path.with_name(path.name + '.before-actors.bak').read_bytes(), original)

    def test_bad_xml_not_modified_or_backed_up(self):
        path = self.nfo()
        path.write_text('<movie><title>Broken')
        original = path.read_bytes()
        with self.assertRaises(ElementTree.ParseError):
            patch_nfo(path, ['Actress'])
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(path.with_name(path.name + '.before-actors.bak').exists())

    def test_atomic_replace_failure_preserves_nfo(self):
        path = self.nfo()
        original = path.read_bytes()
        with patch('ActorRepair.os.replace', side_effect=OSError('disk error')):
            with self.assertRaises(OSError):
                patch_nfo(path, ['Actress'])
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(list(self.videos.glob('*.tmp')), [])

    def test_cache_fills_two_films_with_same_actor_without_network(self):
        paths = [self.nfo('ABC-123'), self.nfo('ABC-124', 'ABC-124')]
        self.cached(['Actress'])
        second = self.cache / 'ABC/ABC-124.json'
        second.write_text(json.dumps({'Car': 'ABC-124', 'Title': 'Second title', 'Actors': ['Actress']}))
        scrape = Mock()
        stats = repair_directory(self.videos, self.handler, self.cache, scrape=scrape)
        scrape.assert_not_called()
        self.assertEqual(stats['updated'], 2)
        self.assertEqual([ElementTree.parse(path).findtext('actor/name') for path in paths], ['Actress'] * 2)

    def test_multipart_queries_once_and_preserves_cached_plot(self):
        paths = [self.nfo('ABC-123-cd1'), self.nfo('ABC-123-cd2')]
        cache = self.cached([])
        entries = json.loads(cache.read_text())
        entries['Plot'] = 'Cached plot'
        cache.write_text(json.dumps(entries))
        def scrape(file, model, url, proxy):
            self.assertEqual(file.Name, '仓库KnownCode.mp4')
            model.Car = 'ABC-123'
            model.Title = 'Fetched title'
            model.Actors = ['Actress']
            return ScrapeStatusEnum.success, []
        get = Mock(side_effect=scrape)
        video = self.videos / 'ABC-123.mp4'
        video.write_bytes(b'video fixture')
        stats = repair_directory(self.videos, self.handler, self.cache, scrape=get)
        self.assertEqual(stats['updated'], 2)
        get.assert_called_once()
        self.assertEqual(video.read_bytes(), b'video fixture')
        self.assertEqual(json.loads(cache.read_text())['Plot'], 'Cached plot')
        self.assertTrue(all(ElementTree.parse(path).findtext('actor/name') == 'Actress' for path in paths))

    def test_blocked_request_stops_and_preserves_all_nfos(self):
        paths = [self.nfo('ABC-123-cd1'), self.nfo('ABC-123-cd2')]
        originals = [path.read_bytes() for path in paths]
        get = Mock(side_effect=SourceUnavailableError('HTTP 403'))
        stats = repair_directory(self.videos, self.handler, self.cache, scrape=get)
        get.assert_called_once()
        self.assertEqual(stats['pending'], 2)
        self.assertEqual([path.read_bytes() for path in paths], originals)

    def test_no_actors_returned_does_not_erase_existing_metadata(self):
        path = self.nfo()
        original = path.read_bytes()
        get = Mock(return_value=(ScrapeStatusEnum.db_not_found, []))
        stats = repair_directory(self.videos, self.handler, self.cache, scrape=get)
        self.assertEqual(stats['missing'], 1)
        self.assertEqual(path.read_bytes(), original)

    def test_existing_actors_skip_network_and_apply_user_alias(self):
        path = self.nfo(actors='<actor><name>Alias</name><thumb>local.jpg</thumb><role>Existing role</role></actor>')
        get = Mock()
        stats = repair_directory(self.videos, self.handler, self.cache, {'Alias': 'Canonical'}, scrape=get)
        get.assert_not_called()
        self.assertEqual(stats['updated'], 1)
        self.assertEqual(ElementTree.parse(path).findtext('actor/name'), 'Canonical')
        self.assertEqual(ElementTree.parse(path).findtext('actor/thumb'), 'local.jpg')
        self.assertEqual(ElementTree.parse(path).findtext('actor/role'), 'Existing role')


if __name__ == '__main__':
    unittest.main()
