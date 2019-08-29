import pytest

from pubtools._pulp.services import Services


def test_cannot_use_directly():
    """Services class can't be used directly, as 'args' must be overridden."""

    svc = Services()

    with pytest.raises(NotImplementedError):
        assert svc.fastpurge_client
