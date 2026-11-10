from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from Class.MyError import SourceUnavailableError
from Functions.Web import Http
from Functions.Web.Javdb import get_db_html

GATE = '<html><title>JavDB</title><p>此内容需要登入才能查看或操作</p></html>'
RESULT = '<html><title>JavDB</title><div class="movie-list">Results</div></html>'


def response(code, body='', headers=None):
    result = requests.Response()
    result.status_code = code
    result.url = 'https://example.test/search?q=ABC-123'
    result._content = body.encode('utf-8')
    result._content_consumed = True
    result.headers.update(headers or {})
    return result


class RefreshRetryTests(unittest.TestCase):
    def setUp(self):
        Http.reset_sources()
        pacer = patch.object(Http, '_pace')
        pacer.start()
        self.addCleanup(pacer.stop)
        self.addCleanup(Http.reset_sources)

    def test_403_then_success_reuses_session_and_preserves_cookies(self):
        # A real Session prepares the retry; only its network send is replaced.
        session = requests.Session()
        seen = []
        def send(prepared, **kwargs):
            seen.append(prepared)
            result = response(403 if len(seen) == 1 else 200, RESULT)
            if len(seen) == 1:
                # Model a cookie the server may set on its initial response.
                session.cookies.set('refresh_fixture', 'test-only', domain='example.test', path='/')
            return result
        with patch.object(Http.requests, 'Session', return_value=session) as factory, \
                patch.object(session, 'send', side_effect=send), patch.object(Http, 'sleep') as sleep:
            self.assertEqual(get_db_html('https://example.test/search?q=ABC-123', {}), RESULT)
            factory.assert_called_once()
            self.assertEqual(len(seen), 2)
            self.assertIn('refresh_fixture=test-only', seen[1].headers['Cookie'])
            sleep.assert_called_once_with(10.0)
        self.assertNotIn('example.test', Http._failed_sources)

    def test_200_gate_then_results_is_retried_not_parsed(self):
        with patch.object(Http, '_request') as get, patch.object(Http, 'sleep') as sleep:
            get.return_value.__enter__.side_effect = [response(200, GATE), response(200, RESULT)]
            self.assertEqual(get_db_html('https://example.test/search', {}), RESULT)
            self.assertEqual(get.call_count, 2)
            sleep.assert_called_once_with(10.0)

    def test_persistent_403_stops_after_one_retry(self):
        with patch.object(Http, '_request') as get, patch.object(Http, 'sleep') as sleep:
            get.return_value.__enter__.side_effect = [response(403), response(403)]
            with self.assertRaisesRegex(SourceUnavailableError, 'HTTP 403'):
                get_db_html('https://example.test/search', {})
            self.assertEqual(get.call_count, 2)
            sleep.assert_called_once_with(10.0)
            with self.assertRaises(SourceUnavailableError):
                get_db_html('https://example.test/next', {})
            self.assertEqual(get.call_count, 2)

    def test_persistent_gate_stops_after_one_retry(self):
        with patch.object(Http, '_request') as get, patch.object(Http, 'sleep'):
            get.return_value.__enter__.side_effect = [response(200, GATE), response(200, GATE)]
            with self.assertRaisesRegex(SourceUnavailableError, '登录提示页'):
                get_db_html('https://example.test/search', {})
            self.assertEqual(get.call_count, 2)

    def test_regular_navigation_login_link_is_not_a_gate(self):
        self.assertFalse(Http._is_temporary_gate('<nav><a href="/login">登入</a></nav>'))
        self.assertTrue(Http._is_temporary_gate('<p>此內容需要<b>登入</b>才能查看或操作</p>'))

    def test_respects_retry_after(self):
        with patch.object(Http, '_request') as get, patch.object(Http, 'sleep') as sleep:
            get.return_value.__enter__.side_effect = [response(403, headers={'Retry-After': '30'}), response(200, RESULT)]
            get_db_html('https://example.test/search', {})
            sleep.assert_called_once_with(30.0)

    def test_long_retry_after_pauses_without_early_request(self):
        with patch.object(Http, '_request') as get, patch.object(Http, 'sleep') as sleep:
            get.return_value.__enter__.return_value = response(403, headers={'Retry-After': '120'})
            with self.assertRaises(SourceUnavailableError):
                get_db_html('https://example.test/search', {})
            self.assertEqual(get.call_count, 1)
            sleep.assert_not_called()

    def test_other_sources_do_not_automatically_retry_403(self):
        with patch.object(Http, '_request') as get, patch.object(Http, 'sleep') as sleep:
            get.return_value.__enter__.return_value = response(403)
            with self.assertRaises(SourceUnavailableError):
                Http.get_html('https://example.test/search', {}, ('Other source',))
            self.assertEqual(get.call_count, 1)
            sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
