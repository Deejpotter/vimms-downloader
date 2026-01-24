from download_vimms import VimmsDownloader
from types import SimpleNamespace


def test_get_download_url_handles_post_form(monkeypatch):
    html = """
    <form action="//dl3.vimm.net/" method="POST" id="dl_form">
      <input type="hidden" name="mediaId" value="6590">
      <button type="submit">Download</button>
    </form>
    """

    dl = VimmsDownloader(download_dir='.', system='GC')

    # Mock session.get to return the HTML
    monkeypatch.setattr(dl, 'session', SimpleNamespace())
    def fake_get(url, headers=None, verify=None):
            return SimpleNamespace(status_code=200, content=html.encode('utf-8'), raise_for_status=lambda: None)
    def fake_post(url, data=None, headers=None, verify=None, allow_redirects=None):
            return SimpleNamespace(status_code=200, url='https://dl3.vimm.net/?mediaId=6590', raise_for_status=lambda: None, headers={})
    dl.session.get = fake_get
    dl.session.post = fake_post

    url = dl.get_download_url('https://vimm.net/vault/7818', '6590')
    assert url == 'https://dl3.vimm.net/?mediaId=6590'
