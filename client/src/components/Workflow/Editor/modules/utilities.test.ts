import { describe, expect, it } from "vitest";

import { getStateUpgradeMessages } from "./utilities";

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
