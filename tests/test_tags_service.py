"""Unit tests for TagsService."""

import pytest

from app.core.exceptions import ValidationException
from app.models.schemas import TagCreateRequest


def test_create_list_and_delete_tags(tags_service):
    first = tags_service.create_tag(TagCreateRequest(name="alpha"))
    second = tags_service.create_tag(TagCreateRequest(name="beta"))

    listing = tags_service.get_tags(limit=10, offset=0)

    assert listing.total == 2
    assert {tag.name for tag in listing.tags} == {"alpha", "beta"}

    assert tags_service.delete_tag(first.id) is True

    listing_after_delete = tags_service.get_tags(limit=10, offset=0)
    assert listing_after_delete.total == 1
    assert listing_after_delete.tags[0].name == "beta"


def test_duplicate_tag_creation_raises(tags_service):
    tags_service.create_tag(TagCreateRequest(name="repeat"))

    with pytest.raises(ValidationException):
        tags_service.create_tag(TagCreateRequest(name="repeat"))
