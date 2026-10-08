"""Integration tests for grants to compute on Crypt4GH-protected datasets."""

import base64
import io
import json
import struct
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from sqlalchemy import select

from galaxy.model import DatasetProtectionGrant
from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


def crypt4gh_header(*packets: bytes) -> bytes:
    header = struct.pack("<8sII", b"crypt4gh", 1, len(packets))
    for packet in packets:
        header += struct.pack("<I", len(packet) + 4) + packet
    return header


USER_HEADER = crypt4gh_header(b"sealed-to-the-user-key")
COMPUTE_HEADER = base64.b64encode(crypt4gh_header(b"sealed-to-the-compute-key")).decode()


def grant_payload(**overrides) -> dict:
    payload = {
        "scheme": "crypt4gh",
        "crypt4gh_compute_header": COMPUTE_HEADER,
        "crypt4gh_compute_keypair_id": "cnk:abcdef0123456789",
        "crypt4gh_compute_keypair_expiration_date": (datetime.now(timezone.utc) + timedelta(days=6)).isoformat(),
    }
    payload.update(overrides)
    return payload


class TestCrypt4GHGrantsIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["crypt4gh_enabled"] = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def _upload_protected(self, history_id: str) -> dict:
        return self.dataset_populator.new_dataset(
            history_id,
            content=io.BytesIO(USER_HEADER + b"encrypted payload"),
            name="reads.fastqsanger.c4gh",
            file_type="auto",
            wait=True,
        )

    def _protection(self, dataset_id: str) -> dict:
        response = self._get(f"datasets/{dataset_id}/protection")
        response.raise_for_status()
        return response.json()

    def _grant(self, dataset_id: str, payload: dict | None = None):
        return self._put(
            f"datasets/{dataset_id}/protection", grant_payload() if payload is None else payload, json=True
        )

    def _copy_to_history(self, history_id: str, dataset_id: str) -> dict:
        response = self._post(
            f"histories/{history_id}/contents", {"source": "hda", "content": dataset_id, "type": "dataset"}, json=True
        )
        response.raise_for_status()
        return response.json()

    def _grants_for_dataset(self, dataset_id: str) -> list[DatasetProtectionGrant]:
        sa_session = self._app.model.session
        hda = self._get(f"datasets/{dataset_id}").json()
        decoded_dataset_id = self._app.security.decode_id(hda["dataset_id"])
        sa_session.expire_all()
        stmt = select(DatasetProtectionGrant).filter_by(dataset_id=decoded_dataset_id)
        return list(sa_session.scalars(stmt))

    def test_upload_is_protected_but_not_ready(self, history_id):
        dataset = self._upload_protected(history_id)
        assert dataset["extension"] == "fastqsanger.c4gh"
        status = self._protection(dataset["id"])
        assert status["protected"] is True
        assert status["scheme"] == "crypt4gh"
        assert status["ready"] is False

    def _change_datatype(self, history_id: str, dataset_id: str, datatype: str):
        return self._put(f"histories/{history_id}/contents/{dataset_id}", {"datatype": datatype}, json=True)

    def test_encrypted_datasets_keep_an_encrypted_datatype(self, history_id):
        dataset = self._upload_protected(history_id)
        response = self._change_datatype(history_id, dataset["id"], "fastqsanger")
        self._assert_status_code_is(response, 400)
        assert "only be changed to another encrypted datatype" in response.json()["err_msg"]
        response = self._change_datatype(history_id, dataset["id"], "c4gh")
        self._assert_status_code_is(response, 200)
        assert self._protection(dataset["id"])["protected"] is True

    def test_plain_datasets_cant_get_an_encrypted_datatype(self, history_id):
        dataset = self.dataset_populator.new_dataset(history_id, content="1\t2\n", wait=True)
        response = self._change_datatype(history_id, dataset["id"], "tabular.c4gh")
        self._assert_status_code_is(response, 400)
        assert "can't be changed to an encrypted datatype" in response.json()["err_msg"]

    def test_bulk_datatype_changes_keep_encrypted_datasets_encrypted(self, history_id):
        encrypted = self._upload_protected(history_id)
        plain = self.dataset_populator.new_dataset(history_id, content="1\t2\n", wait=True)
        payload = {"operation": "change_datatype", "params": {"type": "change_datatype", "datatype": "tabular"}}
        response = self._put(f"histories/{history_id}/contents/bulk", payload, json=True)
        self._assert_status_code_is(response, 200)
        result = response.json()
        assert result["success_count"] == 1, result
        assert [error["item"]["id"] for error in result["errors"]] == [encrypted["id"]], result
        self.dataset_populator.wait_for_history(history_id)
        assert (
            self.dataset_populator.get_history_dataset_details(history_id, content_id=plain["id"])["extension"]
            == "tabular"
        )
        details = self.dataset_populator.get_history_dataset_details(history_id, content_id=encrypted["id"])
        assert details["extension"] == "fastqsanger.c4gh"

    def test_plain_dataset_is_not_protected(self, history_id):
        dataset = self.dataset_populator.new_dataset(history_id, content="1\t2\n", wait=True)
        assert self._protection(dataset["id"]) == {
            "protected": False,
            "scheme": None,
            "ready": False,
            "expires_at": None,
        }
        response = self._grant(dataset["id"])
        self._assert_status_code_is(response, 400)

    def test_grant_makes_dataset_ready_and_is_never_returned(self, history_id):
        dataset = self._upload_protected(history_id)
        response = self._grant(dataset["id"])
        self._assert_status_code_is(response, 200)
        assert response.json()["ready"] is True
        assert response.json()["expires_at"]
        assert self._protection(dataset["id"])["ready"] is True

        # The compute header is a bearer capability, it must not be exposed anywhere.
        details = self._get(f"datasets/{dataset['id']}", data={"view": "detailed"}).json()
        contents = self._get(f"histories/{history_id}/contents", data={"v": "dev", "keys": "metadata"}).json()
        for serialized in (details, contents, response.json()):
            assert COMPUTE_HEADER not in json.dumps(serialized)
        assert not any(key.startswith("metadata_crypt4gh_compute") for key in details)

    def test_grant_replaces_previous_grant(self, history_id):
        dataset = self._upload_protected(history_id)
        self._assert_status_code_is(self._grant(dataset["id"]), 200)
        replacement = grant_payload(crypt4gh_compute_keypair_id="cnk:replacement")
        self._assert_status_code_is(self._grant(dataset["id"], replacement), 200)
        grants = self._grants_for_dataset(dataset["id"])
        assert [grant.key_ref for grant in grants] == ["cnk:replacement"]

    def test_invalid_grants_are_rejected(self, history_id):
        dataset = self._upload_protected(history_id)
        not_a_header = base64.b64encode(b"definitely not a crypt4gh header").decode()
        header_with_body = base64.b64encode(crypt4gh_header(b"packet") + b"body").decode()
        in_a_week = datetime.now(timezone.utc) + timedelta(days=7)
        for invalid in (
            {"crypt4gh_compute_header": "not base64!"},
            {"crypt4gh_compute_header": not_a_header},
            {"crypt4gh_compute_header": header_with_body},
            {"crypt4gh_compute_keypair_id": "has spaces"},
            {"crypt4gh_compute_keypair_expiration_date": in_a_week.replace(tzinfo=None).isoformat()},
            {"crypt4gh_compute_keypair_expiration_date": (in_a_week - timedelta(days=14)).isoformat()},
            {"crypt4gh_compute_keypair_expiration_date": (in_a_week + timedelta(days=365)).isoformat()},
            {"scheme": "other"},
        ):
            response = self._grant(dataset["id"], grant_payload(**invalid))
            assert response.status_code in (400, 422), f"{invalid} -> {response.status_code}"
        assert self._protection(dataset["id"])["ready"] is False

    def test_owner_copy_keeps_grant(self, history_id):
        dataset = self._upload_protected(history_id)
        self._assert_status_code_is(self._grant(dataset["id"]), 200)
        other_history_id = self.dataset_populator.new_history()
        copy = self._copy_to_history(other_history_id, dataset["id"])
        assert self._protection(copy["id"])["ready"] is True

    def test_shared_copy_does_not_carry_grant(self, history_id):
        dataset = self._upload_protected(history_id)
        self._assert_status_code_is(self._grant(dataset["id"]), 200)
        self.dataset_populator.make_public(history_id)

        with self._different_user("crypt4gh_recipient@bx.psu.edu"):
            # Read access to the shared dataset does not include the owner's grant ...
            assert self._protection(dataset["id"])["ready"] is False
            recipient_history_id = self.dataset_populator.new_history()
            copy = self._copy_to_history(recipient_history_id, dataset["id"])
            # ... and neither does a copy in the recipient's own history.
            assert self._protection(copy["id"])["ready"] is False
            # The recipient can only register a grant of their own.
            self._assert_status_code_is(self._grant(copy["id"]), 200)
            assert self._protection(copy["id"])["ready"] is True

        grants = self._grants_for_dataset(dataset["id"])
        assert len(grants) == 2
        assert len({grant.user_id for grant in grants}) == 2

    def test_inaccessible_dataset_cannot_be_granted(self, history_id):
        dataset = self._upload_protected(history_id)
        self.dataset_populator.make_private(history_id, dataset["id"])
        with self._different_user("crypt4gh_stranger@bx.psu.edu"):
            self._assert_status_code_is(self._grant(dataset["id"]), 403)
            self._assert_status_code_is(self._get(f"datasets/{dataset['id']}/protection"), 403)

    def test_purge_disables_grants(self, history_id):
        dataset = self._upload_protected(history_id)
        self._assert_status_code_is(self._grant(dataset["id"]), 200)
        assert self._protection(dataset["id"])["ready"] is True
        self.dataset_populator.delete_dataset(history_id, dataset["id"], purge=True, wait_for_purge=True)
        assert self._protection(dataset["id"])["ready"] is False
        self._assert_status_code_is(self._grant(dataset["id"]), 400)


class TestCrypt4GHGrantsDisabledIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_crypt4gh_upload_is_not_protected_when_disabled(self, history_id):
        dataset = self.dataset_populator.new_dataset(
            history_id,
            content=io.BytesIO(USER_HEADER + b"encrypted payload"),
            name="reads.fastqsanger.c4gh",
            file_type="auto",
            wait=True,
        )
        assert not dataset["extension"].endswith("c4gh")
        assert self._get(f"datasets/{dataset['id']}/protection").json()["protected"] is False
        response = self._put(f"datasets/{dataset['id']}/protection", grant_payload(), json=True)
        self._assert_status_code_is(response, 403)
