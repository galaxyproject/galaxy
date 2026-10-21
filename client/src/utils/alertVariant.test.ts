import { describe, expect, it } from "vitest";

import { alertVariant } from "./alertVariant";

describe("alertVariant", () => {
    it.each([
        ["done", "success"],
        ["error", "danger"],
        ["info", "info"],
        ["warning", "warning"],
        ["primary", "primary"],
    ])("maps the Galaxy status %s to the alert variant %s", (status, variant) => {
        expect(alertVariant(status)).toBe(variant);
    });

    it.each([undefined, null, ""])("leaves an unset status (%s) to the alert default", (status) => {
        expect(alertVariant(status)).toBeUndefined();
    });
});
