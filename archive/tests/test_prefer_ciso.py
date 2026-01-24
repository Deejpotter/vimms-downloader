from downloader_lib.parse import resolve_download_form
from types import SimpleNamespace


def test_prefer_ciso_over_rvz():
    html = '''
    <html>
      <body>
        <a href="//dl3.vimm.net/?mediaId=111">Super Mario.rvz</a>
        <a href="//dl3.vimm.net/?mediaId=222">Super Mario.ciso</a>
      </body>
    </html>
    '''

    # Simple session stub (not used for anchors)
    session = SimpleNamespace()

    url = resolve_download_form(html, session, 'http://example.com', '999', logger=None)
    assert url == 'https://dl3.vimm.net/?mediaId=222'