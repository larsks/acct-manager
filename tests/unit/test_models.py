# pylint: disable=missing-class-docstring,missing-function-docstring,redefined-outer-name
# type: ignore

"""Test model validation"""

import pydantic
import pytest

from acct_manager import models


def test_scaledvalue():
    s = models.ScaledValue(base=1, coefficient=1)
    assert s.resolve(2) == "2"


def test_scaledvalue_fixed():
    s = models.ScaledValue(base=1, coefficient=0)
    assert s.resolve(2) == "1"


def test_scaledvalue_units():
    s = models.ScaledValue(base=1, coefficient=1, units="foo")
    assert s.resolve(2) == "2foo"


def test_quotarequest_invalid_multiplier():
    with pytest.raises(ValueError):
        models.QuotaRequest(multiplier=0)


def test_quotarequest():
    q = models.QuotaRequest(multiplier=1)
    assert q.multiplier == 1


def test_namespacedmetadata_no_namespace():
    with pytest.raises(pydantic.ValidationError):
        models.NamespacedMetadata(name="foo")


def test_project():
    p = models.Project(metadata=models.Metadata(name="test-project"))
    assert p.metadata.name == "test-project"


def test_project_invalid_name():
    with pytest.raises(pydantic.ValidationError):
        models.Project(metadata=models.Metadata(name="invalid name"))


def test_group_ensure_list():
    g = models.Group(metadata=models.Metadata(name="test-group"), users=None)
    assert g.users == []
