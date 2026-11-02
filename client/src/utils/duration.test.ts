import { describe, expect, it } from "vitest";

import { formatDurationSeconds } from "./duration";

describe("formatDurationSeconds", () => {
    it.each([
        [60, "1 minute"],
        [1800, "30 minutes"],
        [3600, "1 hour"],
        [43200, "12 hours"],
        [86400, "24 hours"],
        [129600, "36 hours"],
        [172800, "2 days"],
        [604800, "7 days"],
    ])("formats %s seconds as %s", (seconds, label) => {
        expect(formatDurationSeconds(seconds)).toBe(label);
    });

    it.each([undefined, null, 0, -60, Number.NaN, Number.POSITIVE_INFINITY, "86400"])(
        "returns undefined for %s",
        (seconds) => {
            expect(formatDurationSeconds(seconds as number)).toBeUndefined();
        },
    );
});
