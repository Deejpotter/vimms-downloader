from pathlib import Path
from download_vimms import VimmsDownloader


def test_downloader_accepts_windows_style_path(monkeypatch):
    # Prevent actual filesystem writes by mocking Path.mkdir
    monkeypatch.setattr(Path, 'mkdir', lambda self, *args, **kwargs: None)

    win_path = 'H:/Games/ROMs'
    dl = VimmsDownloader(download_dir=win_path, system='DS', project_root=None)

    assert str(dl.download_dir).replace('\\', '/') == win_path
