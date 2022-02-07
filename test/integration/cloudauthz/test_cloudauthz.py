"""
You may run this test using the following command:
./run_tests.sh test/integration/cloudauthz/test_cloudauthz.py:DefineCloudAuthzTestCase.test_post_cloudauthz_without_authn -s
"""

import json

from galaxy_test.driver import integration_util


class DefineCloudAuthzTestCase(integration_util.IntegrationTestCase):
    framework_tool_and_types = True

    def test_post_cloudauthz_without_authn(self):
        """
        This test asserts if a cloudauthz object
        can be successfully posted to the cloudauthz API
        (i.e., api/cloud/authz).
        """
        provider = "azure"
        tenant_id = "abc"
        client_id = "def"
        client_secret = "ghi"
        with self._different_user("vahid@test.com"):

            # The payload for the POST API.
            payload = {
                "provider": provider,
                "config": json.dumps({"tenant_id": tenant_id, "client_id": client_id, "client_secret": client_secret}),
            }

            response = self._post(path="cloud/authz", data=payload)
            response.raise_for_status()
            cloudauthz = response.json()

            assert cloudauthz["provider"] == provider
