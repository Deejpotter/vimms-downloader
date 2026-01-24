from utils.constants import ROM_EXTENSIONS, ARCHIVE_EXTENSIONS, USER_AGENTS


def test_constants_contain_common_exts():
    assert '.nds' in ROM_EXTENSIONS
    assert '.iso' in ROM_EXTENSIONS
    assert '.zip' in ARCHIVE_EXTENSIONS


def test_user_agents_populated():
    assert isinstance(USER_AGENTS, list)
    assert len(USER_AGENTS) > 0
