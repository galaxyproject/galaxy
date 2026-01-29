from galaxy.objectstore.badges import read_badges


def test_read_config_ignores_galaxy_set_badges():
    config = {"badges": [{"source": "galaxy", "type": "restricted", "message": "private_storage"}]}
    res = read_badges(config)
    assert len(res) == 0


def test_exception_on_unknown_badge_type():
    config = {"badges": [{"type": "cool_custom", "message": "private_storage"}]}
    exc = None
    try:
        read_badges(config)
    except Exception as e:
        exc = e
    assert exc is not None
