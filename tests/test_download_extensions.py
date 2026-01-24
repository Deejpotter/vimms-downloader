from pathlib import Path
from types import SimpleNamespace
from download_vimms import VimmsDownloader


def test_download_accepts_rvz_and_ciso(tmp_path, monkeypatch):
    dl = VimmsDownloader(download_dir=str(tmp_path), system='GC', detect_existing=False)

    # Mock get_download_url to return a URL (we won't care about its value)
    monkeypatch.setattr(dl, 'get_download_url', lambda page, gid: 'https://dl3.vimm.net/?mediaId=6590')

    # Mock session.get to return a response-like object with Content-Disposition header
    content = b'1234567890'
    def fake_get(url, headers=None, verify=None, stream=None, allow_redirects=None, **kwargs):
        # Return an object that has headers, iter_content, and status_code
        return SimpleNamespace(
            status_code=200,
            headers={'Content-Disposition': 'attachment; filename="Super Mario.rvz"', 'content-length': str(len(content))},
            iter_content=lambda chunk_size=8192: [content],
            raise_for_status=lambda: None
        )

    dl.session.get = fake_get

    # Create a fake game dict
    game = {'name': 'Super Mario', 'page_url': 'https://vimm.net/vault/123', 'game_id': '123'}

    ok = dl.download_game(game)
    assert ok is True

    # Verify file exists with .rvz extension
    files = list(tmp_path.iterdir())
    assert any(p.name.endswith('.rvz') for p in files)

    # Now test .ciso
    # Remove only the previously downloaded .rvz (leave logs intact)
    for p in tmp_path.iterdir():
        if p.name.endswith('.rvz'):
            p.unlink()

    def fake_get_ciso(url, headers=None, verify=None, stream=None, allow_redirects=None, **kwargs):
        return SimpleNamespace(
            status_code=200,
            headers={'Content-Disposition': 'attachment; filename="Legend.ciso"', 'content-length': str(len(content))},
            iter_content=lambda chunk_size=8192: [content],
            raise_for_status=lambda: None
        )

    dl.session.get = fake_get_ciso
    game2 = {'name': 'Legend', 'page_url': 'https://vimm.net/vault/456', 'game_id': '456'}
    ok2 = dl.download_game(game2)
    assert ok2 is True

    files2 = list(tmp_path.iterdir())
    assert any(p.name.endswith('.ciso') for p in files2)
