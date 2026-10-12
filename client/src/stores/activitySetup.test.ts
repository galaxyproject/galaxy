import { describe, expect, it } from "vitest";

import { type ActivityAvailability, isActivityAvailable } from "./activitySetup";

const enabledAvailability = {
    canUseUnprivilegedTools: true,
    config: { interactivetools_enable: true, llm_api_configured: true },
} satisfies ActivityAvailability;

describe("isActivityAvailable", () => {
    it("offers an ungated activity whatever the gates say", () => {
        expect(isActivityAvailable("tools", { canUseUnprivilegedTools: false, config: {} })).toBe(true);
    });

    it("hides user-defined tools without the permission", () => {
        expect(isActivityAvailable("user-defined-tools", enabledAvailability)).toBe(true);
        expect(
            isActivityAvailable("user-defined-tools", { ...enabledAvailability, canUseUnprivilegedTools: false }),
        ).toBe(false);
    });

    it("hides interactive tools unless the instance enables them", () => {
        expect(isActivityAvailable("interactivetools", enabledAvailability)).toBe(true);
        expect(
            isActivityAvailable("interactivetools", {
                ...enabledAvailability,
                config: { interactivetools_enable: false },
            }),
        ).toBe(false);
    });

    it("hides GalaxyAI unless an LLM api is configured", () => {
        expect(isActivityAvailable("galaxyai", enabledAvailability)).toBe(true);
        expect(isActivityAvailable("galaxyai", { ...enabledAvailability, config: { llm_api_configured: false } })).toBe(
            false,
        );
    });

    it("hides configured activities when their flags are omitted", () => {
        const availability = { canUseUnprivilegedTools: true, config: {} };
        expect(isActivityAvailable("interactivetools", availability)).toBe(false);
        expect(isActivityAvailable("galaxyai", availability)).toBe(false);
    });

    it("treats a configuration that has not loaded yet as closed", () => {
        expect(isActivityAvailable("interactivetools", { canUseUnprivilegedTools: true })).toBe(false);
        expect(isActivityAvailable("galaxyai", { canUseUnprivilegedTools: true })).toBe(false);
    });
});
