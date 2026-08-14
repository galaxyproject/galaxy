"""Base class for Crypt4GH Selenium tests.

Provides a ``SeleniumTestCase`` subclass that configures Galaxy with crypt4gh
settings and helper methods for uploading encrypted datasets and verifying
encrypted outputs.
"""

import io
from pathlib import Path
from typing import Any

from galaxy_test.selenium.framework import (
    SeleniumTestCase,
    UsesHistoryItemAssertions,
)
from .crypt4gh_test_utils import (
    Crypt4ghTestKeys,
    decrypt_bytes,
    encode_header_b64,
    encrypt_bytes,
    extract_header_bytes,
    reencrypt_header,
)


class Crypt4ghIntegrationSeleniumTestCase(SeleniumTestCase, UsesHistoryItemAssertions):
    """Selenium integration test case with crypt4gh transparent staging enabled.

    This is an integration test because it modifies the default Galaxy
    configuration via ``handle_galaxy_config_kwds``.

    The ``mock_recryptor_url`` and ``crypt4gh_keys`` class attributes are set
    by the ``real_driver`` fixture in ``conftest.py`` before the Galaxy server
    starts.
    """

    isolate_galaxy_config = True
    mock_recryptor_url: str = ""
    crypt4gh_keys: Crypt4ghTestKeys

    @classmethod
    def handle_galaxy_config_kwds(cls, config: dict[str, Any]) -> None:
        super().handle_galaxy_config_kwds(config)
        config["enable_crypt4gh_transparent_staging"] = True
        config["crypt4gh_reencryption_service_url"] = cls.mock_recryptor_url
        config["outputs_to_working_directory"] = True
        config["crypt4gh_cleanup_failure_is_job_failure"] = True
        # Metadata must be embedded in the job script.
        config["metadata_strategy"] = "extended"
        # Tool command line must be built on the job side for crypt4gh staging.
        config["tool_evaluation_strategy"] = "remote"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def upload_crypt4gh_dataset(
        self,
        plaintext_filename: str,
        set_compute_metadata: bool = True,
    ) -> dict[str, Any]:
        """Upload a test-data file as a crypt4gh-encrypted dataset.

        1. Reads the plaintext test-data file.
        2. Encrypts it for the user's public key.
        3. Uploads via the API with ``file_type="auto"`` so the registry
           detects magic bytes and infers the inner type from the filename
           (e.g. ``1.txt.c4gh`` → inner type ``txt`` → ext ``txt.c4gh``).
        4. If ``set_compute_metadata`` is True, sets compute metadata
           (compute header, keypair id, expiration date) via
           ``PUT /api/datasets/{id}`` with a nested ``metadata`` dict,
           matching the API path that the UI's recrypt flow uses.
        5. Waits for the dataset to reach the ``ok`` state.

        Returns the dataset details dict.
        """
        keys = self.crypt4gh_keys
        history_id = self.current_history_id()

        # Read plaintext test data
        plaintext_path = Path(self.get_filename(plaintext_filename))
        plaintext = plaintext_path.read_bytes()

        # Encrypt for the user's public key
        encrypted_bytes = encrypt_bytes(plaintext, [keys.user_public_key])

        # Upload from an in-memory stream so the filename still drives the
        # inferred inner type, without creating a temp file in the test harness.
        encrypted_filename = f"{plaintext_filename}.c4gh"
        dataset = self.dataset_populator.new_dataset(
            history_id,
            content=io.BytesIO(encrypted_bytes),
            file_type="auto",
            wait=True,
            name=encrypted_filename,
        )

        if set_compute_metadata:
            # Re-encrypt header for compute keypair (simulates Service A recrypt)
            header_bytes = extract_header_bytes(encrypted_bytes)
            compute_header = reencrypt_header(
                header_bytes,
                keys.user_private_key,
                [keys.compute_public_key],
            )

            self.dataset_populator.update_dataset(
                dataset["id"],
                {
                    "metadata": {
                        "crypt4gh_compute_header": encode_header_b64(compute_header),
                        "crypt4gh_compute_keypair_id": keys.compute_keypair_id,
                        "crypt4gh_compute_keypair_expiration_date": keys.compute_keypair_expiration_date,
                    }
                },
            )

            # Wait for dataset to be ok after metadata update
            self.dataset_populator.wait_for_history(history_id)

        # Return fresh details
        details = self.dataset_populator.get_history_dataset_details(
            history_id,
            dataset_id=dataset["id"],
        )
        return details

    def upload_plain_dataset(
        self,
        plaintext_filename: str,
        file_ext: str = "txt",
    ) -> dict[str, Any]:
        """Upload a plain (non-encrypted) test-data file via the API."""
        history_id = self.current_history_id()
        plaintext_path = Path(self.get_filename(plaintext_filename))
        with open(plaintext_path, "rb") as f:
            dataset = self.dataset_populator.new_dataset(
                history_id,
                content=f,
                file_type=file_ext,
                wait=True,
                name=plaintext_filename,
            )
        return self.dataset_populator.get_history_dataset_details(
            history_id,
            dataset_id=dataset["id"],
        )

    def assert_crypt4gh_output_extension(self, hid: int, expected_extension: str) -> None:
        """Wait for a Crypt4GH output to finish, expand its history item, and assert the wrapped type."""
        self.history_panel_wait_for_hid_ok(hid)
        self.history_panel_ensure_showing_item_details(hid)
        self.assert_item_extension(hid, expected_extension)

    def verify_crypt4gh_output(
        self,
        dataset_id: str,
        expected_content: bytes,
    ) -> None:
        """Download an encrypted output dataset, decrypt it, and verify content."""
        history_id = self.current_history_id()
        content_bytes = self.dataset_populator.get_history_dataset_content(
            history_id,
            dataset_id=dataset_id,
            type="bytes",
        )
        assert isinstance(content_bytes, bytes), "Expected encrypted dataset content as bytes."
        plaintext = decrypt_bytes(content_bytes, self.crypt4gh_keys.user_private_key)
        assert plaintext == expected_content, (
            f"Decrypted content does not match expected.\n"
            f"Expected: {expected_content!r}\n"
            f"Got:      {plaintext!r}"
        )

    def get_test_file_content(self, filename: str) -> bytes:
        """Read a test-data file and return its content as bytes."""
        return Path(self.get_filename(filename)).read_bytes()
