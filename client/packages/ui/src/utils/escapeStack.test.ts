import { afterEach, describe, expect, it } from "vitest";

import { closeEscapeLayer, type EscapeLayer, isTopEscapeLayer, openEscapeLayer } from "./escapeStack";

let firstCanHandle = true;
let secondCanHandle = true;
const first: EscapeLayer = { canHandle: () => firstCanHandle };
const second: EscapeLayer = { canHandle: () => secondCanHandle };

afterEach(() => {
    closeEscapeLayer(first);
    closeEscapeLayer(second);
    firstCanHandle = true;
    secondCanHandle = true;
});

describe("escapeStack", () => {
    it("puts the most recently opened layer on top", () => {
        openEscapeLayer(first);
        openEscapeLayer(second);

        expect(isTopEscapeLayer(second)).toBe(true);
        expect(isTopEscapeLayer(first)).toBe(false);
    });

    it("hands the top back to the previous layer when the top one closes", () => {
        openEscapeLayer(first);
        openEscapeLayer(second);
        closeEscapeLayer(second);

        expect(isTopEscapeLayer(first)).toBe(true);
    });

    it("moves a reopened layer back to the top", () => {
        openEscapeLayer(first);
        openEscapeLayer(second);
        openEscapeLayer(first);

        expect(isTopEscapeLayer(first)).toBe(true);
    });

    it("skips a newer layer that cannot take the key", () => {
        openEscapeLayer(first);
        openEscapeLayer(second);
        secondCanHandle = false;

        expect(isTopEscapeLayer(first)).toBe(true);
        expect(isTopEscapeLayer(second)).toBe(false);
    });

    it("has no top layer when none can take the key", () => {
        openEscapeLayer(first);
        firstCanHandle = false;

        expect(isTopEscapeLayer(first)).toBe(false);
    });
});
