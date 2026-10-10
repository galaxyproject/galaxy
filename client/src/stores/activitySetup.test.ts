import { describe, expect, it } from "vitest";

import { isActivityAvailable } from "./activitySetup";

const OPEN = {
    canUseUnprivilegedTools: true,
    config: { interactivetools_enable: true, llm_api_configured: true },
};

describe("isActivityAvailable", () => {
    it("offers an ungated activity whatever the gates say", () => {
        expect(isActivityAvailable("tools", { canUseUnprivilegedTools: false, config: {} })).toBe(true);
    });

    it("hides user-defined tools without the permission", () => {
        expect(isActivityAvailable("user-defined-tools", OPEN)).toBe(true);
        expect(isActivityAvailable("user-defined-tools", { ...OPEN, canUseUnprivilegedTools: false })).toBe(false);
    });

    it("hides interactive tools unless the instance enables them", () => {
        expect(isActivityAvailable("interactivetools", OPEN)).toBe(true);
        expect(isActivityAvailable("interactivetools", { ...OPEN, config: { interactivetools_enable: false } })).toBe(
            false,
        );
    });

    it("hides GalaxyAI unless an LLM api is configured", () => {
        expect(isActivityAvailable("galaxyai", OPEN)).toBe(true);
        expect(isActivityAvailable("galaxyai", { ...OPEN, config: { llm_api_configured: false } })).toBe(false);
    });

    it("treats a configuration that has not loaded yet as closed", () => {
        expect(isActivityAvailable("interactivetools", { canUseUnprivilegedTools: true })).toBe(false);
        expect(isActivityAvailable("galaxyai", { canUseUnprivilegedTools: true })).toBe(false);
    });
});
