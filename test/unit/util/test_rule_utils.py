from galaxy.util import rules_dsl


def test_rules():
    for test_case in rules_dsl.get_rules_specification():
        rule_set = rules_dsl.RuleSet(test_case)
        if "initial" in test_case:
            initial = test_case["initial"]
            final_data, final_sources = rule_set.apply(initial["data"], initial["sources"])
            expected_final = test_case["final"]
            expected_final_data = expected_final["data"]
            msg = f"Incorrect number of rows, {final_data} != {expected_final_data}"
            assert len(expected_final_data) == len(final_data), msg
            for final_row, expected_final_row in zip(final_data, expected_final_data):
                msg = f"{final_row} != {expected_final_row}"
                assert len(final_row) == len(expected_final_row), msg
                for final_val, expected_final_val in zip(final_row, expected_final_row):
                    assert final_val == expected_final_val, msg
            expected_final_sources = expected_final.get("sources", None)
            if expected_final_sources:
                msg = f"Incorrect number of sources, {expected_final_sources} != {final_sources}"
                assert len(expected_final_sources) == len(final_sources), msg
                for final_source, expected_final_source in zip(final_sources, expected_final_sources):
                    msg = f"{final_source} != {expected_final_source}"
                    assert final_source == expected_final_source, msg

        elif "error" in test_case:
            assert rule_set.has_errors, f"rule [{test_case}] does not contain errors"
        else:
            raise Exception(f"Problem with test case definition [{test_case}].")
