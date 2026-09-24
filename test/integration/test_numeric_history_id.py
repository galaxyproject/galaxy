"""Exercise encoded history IDs that happen to contain only decimal digits."""

import json

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class TestNumericHistoryId(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        # Encode database ID 1 as an all-digit string without mocking ID encoding.
        config["id_secret"] = "converter-history-2513"

    def test_form_submission(self):
        populator = DatasetPopulator(self.galaxy_interactor)
        history_id = populator.new_history()
        assert history_id == "7456249629763929"
        dataset = populator.new_dataset(
            history_id, content="chr1\ttest\texon\t1\t10\t.\t+\t.\tgene_id x\n", file_type="gff", wait=True
        )
        payload = {
            "history_id": history_id,
            "tool_id": "CONVERTER_gff_to_interval_index_0",
            "inputs": {"input1": {"src": "hda", "id": dataset["id"]}},
        }
        control = self._post("tools", data=payload, json=True)
        print(
            f"REPRO JSON status={control.status_code} request_id={control.headers.get('x-request-id')} body={control.text}"
        )
        assert control.status_code == 200
        response = self._post("tools", data={**payload, "inputs": json.dumps(payload["inputs"])})
        print(
            f"REPRO FORM status={response.status_code} request_id={response.headers.get('x-request-id')} body={response.text}"
        )
        history = self._get(f"histories/{history_id}")
        print(f"REPRO history after form status={history.status_code} deleted={history.json().get('deleted')}")
        assert history.status_code == 200
        assert not history.json()["deleted"]
        assert response.status_code == 200, response.text
