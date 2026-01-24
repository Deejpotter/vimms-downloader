from downloader_lib.parse import resolve_download_form
from types import SimpleNamespace

class LogCollector:
    def __init__(self):
        self.msgs = []
    def info(self, *a, **k):
        self.msgs.append(('info', ' '.join(map(str,a))))
    def exception(self, *a, **k):
        self.msgs.append(('exception', ' '.join(map(str,a))))


def test_resolve_logs_form_get():
    html = '''
    <form action="//dl3.vimm.net/" method="GET" id="dl_form">
      <input type="hidden" name="mediaId" value="6500">
      <input type="hidden" name="alt" value="0" disabled="">
      <button type="submit">Download</button>
    </form>
    '''

    logger = LogCollector()
    session = SimpleNamespace()
    session.headers = {}

    url = resolve_download_form(html, session, 'http://example.com', '6500', logger=logger)
    assert url is not None and 'mediaId=6500' in url
    # Ensure logger got a message about the form and inputs
    infos = [m for t,m in logger.msgs if t == 'info']
    assert any('Found download form' in s for s in infos)
    assert any('mediaId' in s for s in infos)


def test_resolve_logs_form_post(monkeypatch):
    html = '''
    <form action="//dl3.vimm.net/" method="POST" id="dl_form">
      <input type="hidden" name="mediaId" value="6590">
      <button type="submit">Download</button>
    </form>
    '''

    logger = LogCollector()
    class FakeResp:
        def __init__(self, url):
            self.url = url
    # Provide a session with a `.post` that returns a response-like object
    session = SimpleNamespace()
    session.headers = {}
    session.post = lambda *a, **k: FakeResp('https://dl3.vimm.net/?mediaId=6590')

    url = resolve_download_form(html, session, 'http://example.com', '6590', logger=logger)
    assert url == 'https://dl3.vimm.net/?mediaId=6590'
    infos = [m for t,m in logger.msgs if t == 'info']
    assert any('Found download form' in s for s in infos)
    assert any('Submitting POST form' in s for s in infos) or any('POST form resolved' in s for s in infos)
