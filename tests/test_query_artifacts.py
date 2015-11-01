"""Test query_artifacts() function."""

from functools import partial

from appveyor_artifacts import query_artifacts


def mock_query_api(url, replies):
    """Mock JSON replies."""
    return replies[url]


def test(monkeypatch):
    """Test everything."""
    # Test empty.
    monkeypatch.setattr('appveyor_artifacts.query_api', lambda _: list())
    assert query_artifacts(['spfxkimxcj6faq57']) == list()

    # Test multiple jobs.
    replies = {
        '/buildjobs/v5wnn9k8auqcqovw/artifacts': [
            {'fileName': 'luajit.exe', 'size': 675840, 'type': 'File'},
            {'fileName': 'luv.dll', 'size': 891392, 'type': 'File'},
            {'fileName': '.coverage', 'size': 123, 'type': 'File'},
            {'fileName': 'no_ext', 'size': 456, 'type': 'File'},
        ],
        '/buildjobs/bpgcbvqmawv1jw06/artifacts': [
            {'fileName': 'luajit.exe', 'size': 539136, 'type': 'File'},
            {'fileName': 'luv.dll', 'size': 718336, 'type': 'File'},
            {'fileName': '.coverage', 'size': 789, 'type': 'File'},
            {'fileName': 'no_ext', 'size': 101, 'type': 'File'},
        ],
    }
    monkeypatch.setattr('appveyor_artifacts.query_api', partial(mock_query_api, replies=replies))
    actual = query_artifacts(['v5wnn9k8auqcqovw', 'bpgcbvqmawv1jw06'])

    expected = [
        ('v5wnn9k8auqcqovw', 'luajit.exe', 675840),
        ('v5wnn9k8auqcqovw', 'luv.dll', 891392),
        ('v5wnn9k8auqcqovw', '.coverage', 123),
        ('v5wnn9k8auqcqovw', 'no_ext', 456),
        ('bpgcbvqmawv1jw06', 'luajit.exe', 539136),
        ('bpgcbvqmawv1jw06', 'luv.dll', 718336),
        ('bpgcbvqmawv1jw06', '.coverage', 789),
        ('bpgcbvqmawv1jw06', 'no_ext', 101),
    ]
    assert actual == expected
