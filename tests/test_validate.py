"""Test validate() function."""

import pytest

from appveyor_artifacts import HandledError, validate


def test(caplog):
    """Test function."""
    config = dict(commit='abc123def456', owner='Robpol86', repo='appveyor_artifacts', tag='v0.0.0')
    validate(config)

    config['tag'] = 'Inv@l*d'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'Invalid git tag obtained.'

    config['tag'] = ''
    validate(config)

    config['repo'] = 'Inv@lid'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'No or invalid repo name obtained.'

    config['owner'] = 'Inv@lid'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'No or invalid repo owner name obtained.'

    config['commit'] = 'invalid'
    with pytest.raises(HandledError):
        validate(config)
    assert caplog.records()[-2].message == 'No or invalid git commit obtained.'
