import { describe, expect, it } from "vitest";

import { getFilledDefaults, getStateUpgradeMessages } from "./utilities";

describe("getStateUpgradeMessages", () => {
    it("flattens nested subworkflow messages into their text", () => {
        const [message] = getStateUpgradeMessages({
            steps: { "1": { name: "Subworkflow", type: "subworkflow", label: "inner" } },
            upgrade_messages: {
                "1": {
                    "Step 1": { version: "Using version '0.2' instead of version '0.0.1'" },
                    "Step 2": { inttest: "Parameter 'inttest': an integer or workflow parameter is required" },
                },
            },
        });

        expect(message!.details).toEqual([
            "Using version '0.2' instead of version '0.0.1'",
            "Parameter 'inttest': an integer or workflow parameter is required",
        ]);
    });

    it("keeps step errors and flat tool messages as they are", () => {
        const [message] = getStateUpgradeMessages({
            steps: { "0": { name: "Tool", type: "tool", label: "", errors: "Tool is not installed" } },
            upgrade_messages: { "0": { param: "Value changed" } },
        });

        expect(message!.details).toEqual(["Tool is not installed", "Value changed"]);
    });

    it("skips steps without messages", () => {
        const messages = getStateUpgradeMessages({
            steps: { "0": { name: "Tool", type: "tool", label: "" } },
            upgrade_messages: {},
        });

        expect(messages).toEqual([]);
    });
});

describe("getFilledDefaults", () => {
    it("reads filled defaults per step, without step errors", () => {
        const data = {
            steps: { "0": { name: "Tool", type: "tool", label: "qc", errors: "Tool is not installed" } },
            upgrade_messages: {},
            filled_defaults: { "0": { kmers: "No value found for 'Kmers'. Using default: '7'." } },
        };
        expect(getFilledDefaults(data)[0]?.details).toEqual(["No value found for 'Kmers'. Using default: '7'."]);
        expect(getStateUpgradeMessages(data)[0]?.details).toEqual(["Tool is not installed"]);
    });

    it("is empty for workflows from servers that don't send filled defaults", () => {
        expect(
            getFilledDefaults({ steps: { "0": { name: "Tool", type: "tool", label: "" } }, upgrade_messages: {} }),
        ).toEqual([]);
    });
});
