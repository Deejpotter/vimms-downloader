from downloader_lib.parse import resolve_download_form
from types import SimpleNamespace
from pathlib import Path

HTML = '''
<html>
  <body>
    <a href="//dl2.vimm.net/?mediaId=111">Download .ciso</a>
    <a href="//dl3.vimm.net/?mediaId=222">Download .rvz</a>
  </body>
</html>
'''

class DummySession:
    def get(self, url, allow_redirects=None, verify=None):
        # Return different responses depending on mediaId in URL
        if 'mediaId=111' in url:
            return SimpleNamespace(status_code=200, url='https://dl2.vimm.net/?mediaId=111', headers={'Content-Disposition': 'attachment; filename="Game.ciso"'}, raise_for_status=lambda: None)
        if 'mediaId=222' in url:
            return SimpleNamespace(status_code=200, url='https://dl3.vimm.net/?mediaId=222', headers={'Content-Disposition': 'attachment; filename="Game.rvz"'}, raise_for_status=lambda: None)
        return SimpleNamespace(status_code=404, url=url, headers={}, raise_for_status=lambda: None)


def test_prefers_rvz_over_ciso():
    session = DummySession()
    url = resolve_download_form(HTML, session, 'http://example.com/game/123', '123', logger=None)
    assert url == 'https://dl3.vimm.net/?mediaId=222'
