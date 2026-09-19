import { describe, expect, it } from "vitest";

import type { PaletteContext } from "../types";
import { navigationProvider } from "./navigation";

function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return {
        canUseUnprivilegedTools: false,
        config: { interactivetools_enable: false, llm_api_configured: false },
        isAdmin: false,
        isAnonymous: false,
        ...overrides,
    };
}

async function search(query: string, ctx: PaletteContext) {
    return navigationProvider.search(query, ctx);
}

describe("navigationProvider", () => {
    it("finds activity destinations by title", async () => {
        const items = await search("workflows", makeCtx());
        const workflows = items.find((i) => i.id === "navigation:workflows");
        expect(workflows?.to).toBe("/workflows/list");
    });

    it("hides login-only activities from anonymous users", async () => {
        const loggedIn = await search("datasets", makeCtx());
        expect(loggedIn.some((i) => i.id === "navigation:datasets")).toBe(true);

        const anonymous = await search("datasets", makeCtx({ isAnonymous: true }));
        expect(anonymous.some((i) => i.id === "navigation:datasets")).toBe(false);
    });

    it("hides interactive tools unless enabled in config", async () => {
        const disabled = await search("interactive", makeCtx());
        expect(disabled.some((i) => i.id === "navigation:interactivetools")).toBe(false);

        const enabled = await search("interactive", makeCtx({ config: { interactivetools_enable: true } }));
        expect(enabled.some((i) => i.id === "navigation:interactivetools")).toBe(true);
    });

    it("hides GalaxyAI unless an LLM api is configured", async () => {
        const disabled = await search("galaxyai", makeCtx());
        expect(disabled.some((i) => i.id === "navigation:galaxyai")).toBe(false);

        const enabled = await search("galaxyai", makeCtx({ config: { llm_api_configured: true } }));
        expect(enabled.some((i) => i.id === "navigation:galaxyai")).toBe(true);
    });

    it("gives panel-only activities a handler instead of a route", async () => {
        const items = await search("invocations", makeCtx());
        const invocations = items.find((i) => i.id === "navigation:invocation");
        expect(invocations).toBeDefined();
        expect(invocations?.to).toBeUndefined();
        expect(invocations?.handler).toBeTypeOf("function");
    });

    it("includes curated destinations that are not activities", async () => {
        const items = await search("preferences", makeCtx());
        const preferences = items.find((i) => i.to === "/user");
        expect(preferences).toBeDefined();
    });

    it("hides login-only curated destinations from anonymous users", async () => {
        const items = await search("preferences", makeCtx({ isAnonymous: true }));
        expect(items.some((i) => i.to === "/user")).toBe(false);
    });

    it("keeps the curated destinations anonymous users may reach", async () => {
        const ctx = makeCtx({ isAnonymous: true });
        expect((await search("about", ctx)).some((i) => i.to === "/about")).toBe(true);
        expect((await search("tours", ctx)).some((i) => i.to === "/tours")).toBe(true);
        expect((await search("datatypes", ctx)).some((i) => i.to === "/datatypes")).toBe(true);
    });

    it("hides notifications unless the notification system is enabled", async () => {
        const disabled = await search("notifications", makeCtx());
        expect(disabled.some((i) => i.to === "/user/notifications")).toBe(false);

        const enabled = await search("notifications", makeCtx({ config: { enable_notification_system: true } }));
        expect(enabled.some((i) => i.to === "/user/notifications")).toBe(true);
    });

    it("does not leak the gating flags onto the rendered rows", async () => {
        const items = await search("preferences", makeCtx());
        const preferences = items.find((i) => i.to === "/user");
        expect(preferences).not.toHaveProperty("anonymous");
        expect(preferences).not.toHaveProperty("available");
    });

    it("does not offer the upload activity (owned by the actions provider)", async () => {
        const items = await search("upload", makeCtx());
        expect(items.some((i) => i.id.startsWith("navigation:upload"))).toBe(false);
        expect(items.some((i) => i.id.startsWith("navigation:beta-upload"))).toBe(false);
    });
});
