from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from xml.etree import ElementTree
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from Class.MyJav import JavFile, JavModel
from Functions.Progress.Completion import is_complete
import Youma
from test_batch_control import make_config, working_directory


class CompletedFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.file = JavFile('ABC-123', 'ABC-123', 'ABC-123 title.mp4', str(self.directory), 1, '', 1)
        Path(self.file.Path).write_bytes(b'fixture')
        self.nfo = self.directory / 'ABC-123 title.nfo'
        self.nfo.write_text('<movie><title>ABC-123 title</title><id>ABC-123</id></movie>', encoding='utf-8')
        for name in ('fanart', 'poster'):
            Image.new('RGB', (20, 30)).save(self.directory / f'ABC-123 title-{name}.jpg')

    def complete(self):
        return is_complete(self.file, True, ['视频', '-fanart.jpg'], ['视频', '-poster.jpg'])

    def test_matching_nfo_and_images_are_complete(self):
        self.assertTrue(self.complete())

    def test_missing_or_corrupt_image_is_not_complete(self):
        poster = self.directory / 'ABC-123 title-poster.jpg'
        poster.unlink()
        self.assertFalse(self.complete())
        poster.write_bytes(b'not an image')
        self.assertFalse(self.complete())

    def test_mismatched_nfo_identity_is_not_complete(self):
        self.nfo.write_text('<movie><title>Other movie</title><id>ABC-124</id></movie>')
        self.assertFalse(self.complete())

    def test_other_file_nfo_does_not_skip_unfinished_video(self):
        self.nfo.rename(self.directory / 'other.nfo')
        self.assertFalse(self.complete())

    def test_incomplete_xml_is_not_skipped_or_rewritten(self):
        text = '<movie><title>ABC-123 title</title><id>ABC-123</id>'
        self.nfo.write_text(text)
        self.assertFalse(self.complete())
        self.assertEqual(self.nfo.read_text(), text)
        self.nfo.write_text(text + '<actor>')
        self.assertFalse(self.complete())

    def test_image_requirement_can_be_disabled(self):
        self.assertTrue(is_complete(self.file, False, [], []))

    def test_custom_metadata_image_name_is_not_guessed(self):
        self.assertFalse(is_complete(self.file, True, ['全部演员', '-fanart.jpg'], ['视频', '-poster.jpg']))

    def test_shared_kodi_sidecars_match_multipart_video(self):
        self.file.Name = 'ABC-123 title-cd1.mp4'
        self.file.Sum_all_episodes = 2
        self.assertTrue(is_complete(self.file, True, ['视频', '-fanart.jpg'], ['视频', '-poster.jpg'], cd_only=True))

    def test_completed_file_skips_network_and_file_mutations(self):
        with working_directory(self.directory):
            handler = make_config()
            handler._bool_nfo = True
            handler._bool_jpg = True
            # Restore default image naming; do not mutate the complete fixture.
            handler._list_name_fanart = ['视频', '-fanart.jpg']
            handler._list_name_poster = ['视频', '-poster.jpg']
            with patch.object(Youma, 'scrape_from_db') as db, patch.object(handler, 'rename_mp4') as rename:
                Youma.Youma(str(self.directory), handler)
                db.assert_not_called()
                rename.assert_not_called()
            handler._skip_complete = False
            self.assertFalse(handler.is_already_organized(self.file))

    def test_new_nfo_writer_emits_closed_movie_document(self):
        with working_directory(self.directory):
            handler = make_config()
            handler._bool_nfo = True
            model = JavModel(Car='ABC-123', Title='Fixture title')
            handler.prefect_dict_for_standard(self.file, model)
            handler.write_nfo(self.file, model, [])
            movie = ElementTree.parse(self.nfo).getroot()
            self.assertEqual(movie.tag, 'movie')
            self.assertEqual(movie.findtext('id'), 'ABC-123')


if __name__ == '__main__':
    unittest.main()
