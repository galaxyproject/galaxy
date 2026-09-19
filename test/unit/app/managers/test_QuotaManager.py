"""
Quota Manager testing.
"""

import pytest

from galaxy import model
from galaxy.exceptions import ActionInputError
from galaxy.managers.quotas import QuotaManager
from .base import BaseTestCase

user1_data = dict(email="user1@example.org", username="user1", password="123456")


def _create_payload(
    name="test quota",
    description="a test quota",
    amount="100 MB",
    operation=None,
    default=None,
    quota_source_label=None,
    in_users=None,
    in_groups=None,
):
    payload: dict = dict(name=name, description=description, amount=amount)
    if operation is not None:
        payload["operation"] = operation
    if default is not None:
        payload["default"] = default
    if quota_source_label is not None:
        payload["quota_source_label"] = quota_source_label
    if in_users is not None:
        payload["in_users"] = in_users
    if in_groups is not None:
        payload["in_groups"] = in_groups
    return payload


class _EditParams:
    """Minimal stand-in for the params object expected by edit_quota / rename_quota."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestQuotaManager(BaseTestCase):
    def set_up_managers(self):
        super().set_up_managers()
        self.quota_manager: QuotaManager = self.app[QuotaManager]

    def test_create_quota_basic(self):
        quota, message = self.quota_manager.create_quota(_create_payload(name="q1", amount="100 MB"))
        assert isinstance(quota, model.Quota)
        assert quota.id is not None
        assert quota.name == "q1"
        assert quota.bytes == 100_000_000
        assert "q1" in message

    def test_create_quota_duplicate_name_raises(self):
        self.quota_manager.create_quota(_create_payload(name="dup"))
        with pytest.raises(ActionInputError, match="already exists"):
            self.quota_manager.create_quota(_create_payload(name="dup"))

    def test_create_quota_invalid_amount_raises(self):
        with pytest.raises(ActionInputError, match="Unable to parse"):
            self.quota_manager.create_quota(_create_payload(amount="not-a-size"))

    def test_create_quota_unlimited(self):
        quota, _ = self.quota_manager.create_quota(_create_payload(name="ulim", amount="unlimited"))
        assert quota.amount is None
        assert quota.bytes == -1

    def test_create_quota_default_registered(self):
        quota, message = self.quota_manager.create_quota(
            _create_payload(name="def-reg", default="registered", operation="=")
        )
        assert quota.default
        assert "Default quota" in message

    def test_create_quota_non_exact_default_raises(self):
        with pytest.raises(ActionInputError, match="Operation for a default quota"):
            self.quota_manager.create_quota(_create_payload(name="bad-default", default="registered", operation="+"))

    def test_create_quota_unlimited_non_exact_raises(self):
        with pytest.raises(ActionInputError, match="Operation for an unlimited quota"):
            self.quota_manager.create_quota(_create_payload(name="ulim-add", amount="unlimited", operation="+"))

    def test_create_quota_with_user(self):
        user1 = self.user_manager.create(**user1_data)
        quota, message = self.quota_manager.create_quota(_create_payload(name="user-q", in_users=[str(user1.id)]))
        assert len(quota.users) == 1
        assert quota.users[0].user == user1
        assert "1 associated users" in message

    @pytest.mark.parametrize(
        "amount, expected_bytes",
        [
            ("500", 500),
            ("10 B", 10),
            ("10 bytes", 10),
            # SI units
            ("1 kB", 1_000),
            ("1 kilobyte", 1_000),
            ("1 kilobytes", 1_000),
            ("4k", 4_000),
            ("1. MB", 1_000_000),
            ("1.0 GB", 1_000_000_000),
            ("2.2 TB", 2_200_000_000_000),
            ("1petabytes", 1_000_000_000_000_000),
            ("1EB", 1_000_000_000_000_000_000),
            # IEC units
            ("1 KiB", 1_024),
            ("1 kibibyte", 1_024),
            ("1 kibibytes", 1_024),
            ("1. MiB", 1_048_576),
            ("1.0 GiB", 1_073_741_824),
            ("2.2 TiB", 2_418_925_581_107),
            ("1pebibytes", 1_125_899_906_842_624),
            ("1EiB", 1_152_921_504_606_846_976),
        ],
    )
    def test_create_quota_various_units(self, amount, expected_bytes):
        name = f"amount-{amount.replace(' ', '_')}"
        quota, _ = self.quota_manager.create_quota(_create_payload(name=name, amount=amount))
        assert quota.bytes == expected_bytes, f"amount={amount!r}: expected {expected_bytes}, got {quota.bytes}"

    @pytest.mark.parametrize(
        "amount, expected_bytes",
        [
            ("1 GB", 1_000_000_000),
            ("1 GiB", 1_073_741_824),
        ],
    )
    def test_edit_quota_change_amount(self, amount, expected_bytes):
        quota, _ = self.quota_manager.create_quota(_create_payload(name="edit-si", amount="100 MB"))
        assert quota.bytes == 100_000_000

        message = self.quota_manager.edit_quota(quota, _EditParams(amount=amount, operation="="))
        assert quota.bytes == expected_bytes
        assert message is not None

    def test_edit_quota_to_unlimited(self):
        quota, _ = self.quota_manager.create_quota(_create_payload(name="edit-unlim", amount="1 GB"))
        assert quota.bytes == 1_000_000_000

        message = self.quota_manager.edit_quota(quota, _EditParams(amount="unlimited", operation="="))
        assert quota.amount is None
        assert quota.bytes == -1
        assert message is not None

    def test_edit_quota_invalid_amount_raises(self):
        quota, _ = self.quota_manager.create_quota(_create_payload(name="edit-bad"))
        with pytest.raises(ActionInputError, match="Unable to parse"):
            self.quota_manager.edit_quota(quota, _EditParams(amount="notasize", operation="="))

    def test_edit_quota_no_change_returns_none(self):
        quota, _ = self.quota_manager.create_quota(_create_payload(name="edit-same", amount="100 MB"))
        result = self.quota_manager.edit_quota(quota, _EditParams(amount="100 MB", operation="="))
        assert result is None

    def test_rename_quota(self):
        quota, _ = self.quota_manager.create_quota(_create_payload(name="old-name"))
        message = self.quota_manager.rename_quota(quota, _EditParams(name="new-name", description="desc"))
        assert quota.name == "new-name"
        assert message is not None and "new-name" in message

    def test_rename_quota_duplicate_raises(self):
        self.quota_manager.create_quota(_create_payload(name="existing"))
        quota, _ = self.quota_manager.create_quota(_create_payload(name="to-rename"))
        with pytest.raises(ActionInputError, match="already exists"):
            self.quota_manager.rename_quota(quota, _EditParams(name="existing", description=""))

    def test_rename_quota_empty_name_raises(self):
        quota, _ = self.quota_manager.create_quota(_create_payload(name="has-name"))
        with pytest.raises(ActionInputError, match="valid name"):
            self.quota_manager.rename_quota(quota, _EditParams(name="", description=""))

    def test_manage_users_for_quota(self):
        user1 = self.user_manager.create(**user1_data)
        quota, _ = self.quota_manager.create_quota(_create_payload(name="manage-users"))
        assert len(quota.users) == 0

        params = _EditParams(in_users=[user1.id], in_groups=[])
        self.quota_manager.manage_users_and_groups_for_quota(quota, params)
        assert len(quota.users) == 1

    def test_manage_users_on_default_quota_raises(self):
        user1 = self.user_manager.create(**user1_data)
        quota, _ = self.quota_manager.create_quota(
            _create_payload(name="default-manage", default="registered", operation="=")
        )
        params = _EditParams(in_users=[user1.id], in_groups=[])
        with pytest.raises(ActionInputError, match="Default quotas"):
            self.quota_manager.manage_users_and_groups_for_quota(quota, params)

    def test_set_unset_quota_default(self):
        quota, _ = self.quota_manager.create_quota(_create_payload(name="make-default"))
        assert not quota.default

        message = self.quota_manager.set_quota_default(quota, _EditParams(default="registered"))
        assert message is not None
        assert len(quota.default) == 1
        assert quota.default[0].type == "registered"

        message = self.quota_manager.unset_quota_default(quota)
        assert message is not None
        assert not quota.default
