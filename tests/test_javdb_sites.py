from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from Functions.Web.Sites import load_sites, save_sites, validate_sites
from Functions.Web import Javdb
from Class.MyError import SourceUnavailableError
from Class.MyEnum import ScrapeStatusEnum
from test_batch_control import make_config, working_directory
from test_javdb_search import SEARCH, DETAIL
from Class.MyJav import JavFile, JavModel
import Youma


class SiteSettingsTests(unittest.TestCase):
    def tearDown(self):
        Javdb.configure_db_sites([])

    def test_defaults_and_roundtrip_custom_sites(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sites.json'
            self.assertEqual(load_sites(path=path), ['https://javdb.com', 'https://javdb580.com'])
            save_sites('https://custom.example/', ['https://backup.example/', 'https://custom.example'], path)
            self.assertEqual(load_sites(path=path), ['https://custom.example', 'https://backup.example'])
            save_sites('https://custom.example', [], path)
            self.assertEqual(load_sites(path=path), ['https://custom.example'])

    def test_rejects_bad_settings_without_overwriting_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sites.json'
            save_sites('https://example.test', [], path)
            original = path.read_bytes()
            for bad in ('', 'javdb.com', 'file:///tmp', 'https://user:pass@example.test', 'https://example.test/v/code', 'https://example.test?q=x', 'https://example.test:wrong'):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    save_sites(bad, [], path)
                self.assertEqual(path.read_bytes(), original)

    def test_failover_after_network_error_remembers_working_site(self):
        Javdb.configure_db_sites(['https://main.example', 'https://backup.example'])
        with patch.object(Javdb, 'get_html', side_effect=[SourceUnavailableError('timeout', allow_mirror=True), 'JavDB search', 'JavDB detail']) as get:
            self.assertEqual(Javdb.get_db_html('https://main.example/search?q=ABC-123&f=all', {}), 'JavDB search')
            Javdb.get_db_html('https://main.example/v/code', {})
        self.assertEqual([call.args[0] for call in get.call_args_list], [
            'https://main.example/search?q=ABC-123&f=all',
            'https://backup.example/search?q=ABC-123&f=all', 'https://backup.example/v/code'])

    def test_denial_or_gate_does_not_rotate_to_backup(self):
        Javdb.configure_db_sites(['https://main.example', 'https://backup.example'])
        for reason in ('HTTP 403', 'HTTP 429', 'login required'):
            with self.subTest(reason=reason), patch.object(Javdb, 'get_html', side_effect=SourceUnavailableError(reason)) as get:
                with self.assertRaises(SourceUnavailableError):
                    Javdb.get_db_html('https://main.example/search?q=x', {})
                self.assertEqual(get.call_count, 1)

    def test_all_unreachable_sites_are_bounded(self):
        Javdb.configure_db_sites(['https://main.example', 'https://backup.example'])
        with patch.object(Javdb, 'get_html', side_effect=SourceUnavailableError('timeout', allow_mirror=True)) as get:
            with self.assertRaises(SourceUnavailableError):
                Javdb.get_db_html('https://main.example/search', {})
            self.assertEqual(get.call_count, 2)

    def test_saved_settings_are_used_by_existing_handler(self):
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            save_sites('https://custom.example', ['https://second.example'])
            handler = make_config()
            self.assertEqual(handler.url_db, 'https://custom.example')
            self.assertEqual(handler.db_sites, ['https://custom.example', 'https://second.example'])

    def test_scraper_extracts_site_cover_and_available_description(self):
        file = JavFile('DLDSS-558', 'DLDSS-558', 'DLDSS-558.mp4', '.', 1, '', 1)
        detail = DETAIL.replace('<title>', '<meta property="og:image" content="/covers/example.jpg"><title>', 1)
        detail = detail.replace('</body>', '') + '<section class="video-description">Available plot</section>'
        with patch.object(Javdb, 'get_db_html', side_effect=[SEARCH, detail]):
            model = JavModel()
            Javdb.scrape_from_db(file, model, 'https://javdb.com', {})
        self.assertEqual(model.CoverDb, 'https://javdb.com/covers/example.jpg')
        self.assertEqual(model.Plot, 'Available plot')

    def test_organizer_uses_javdb_only(self):
        with tempfile.TemporaryDirectory() as base:
            program = Path(base) / 'program'
            program.mkdir()
            videos = Path(base) / 'videos'
            videos.mkdir()
            (videos / 'ABC-123.mp4').write_bytes(b'fixture')
            def scrape(file, model, url, proxy):
                model.Car = 'ABC-123'
                model.Title = 'Fixture'
                model.Javdb = 'Known'
                return ScrapeStatusEnum.success, []
            with working_directory(program):
                handler = make_config()
                with patch.object(Youma, 'scrape_from_db', side_effect=scrape) as db, \
                        patch.object(Youma, 'scrape_from_library') as library, \
                        patch.object(Youma, 'scrape_from_bus') as bus, \
                        patch.object(Youma, 'scrape_from_arzon') as arzon:
                    Youma.Youma(str(videos), handler)
                db.assert_called_once()
                library.assert_not_called()
                bus.assert_not_called()
                arzon.assert_not_called()

    @unittest.skipUnless(sys.platform == 'win32', 'Windows Tk dialog test')
    def test_windows_settings_window_saves_values(self):
        import tkinter as tk
        from ConfigureSites import build_window
        with tempfile.TemporaryDirectory() as directory, working_directory(directory):
            window = build_window(['https://javdb.com', 'https://javdb580.com'], hidden=True)
            try:
                entry = next(widget for widget in window.winfo_children() if isinstance(widget, tk.Entry))
                entry.delete(0, 'end')
                entry.insert(0, 'https://custom.example')
                with patch('tkinter.messagebox.showinfo') as info:
                    next(widget for widget in window.winfo_children() if isinstance(widget, tk.Button)).invoke()
                    info.assert_called_once()
                self.assertEqual(load_sites(), ['https://custom.example', 'https://javdb580.com'])
            finally:
                try:
                    window.destroy()
                except tk.TclError:
                    pass


if __name__ == '__main__':
    unittest.main()
