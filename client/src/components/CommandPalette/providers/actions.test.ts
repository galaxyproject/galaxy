import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import type { PaletteContext } from "../types";
import { actionsProvider } from "./actions";

function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return {
        canUseUnprivilegedTools: false,
        config: {},
        isAdmin: false,
        isAnonymous: false,
        ...overrides,
    };
}

async function search(query: string, ctx: PaletteContext) {
    return actionsProvider.search(query, ctx);
}

describe("actionsProvider", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("lists all actions on an empty query", () => {
        const items = actionsProvider.emptyQueryItems?.(makeCtx()) ?? [];
        expect(items.length).toBeGreaterThan(0);
        expect(items.every((i) => i.id.startsWith("actions:"))).toBe(true);
    });

    it("finds the upload action, also for anonymous users", async () => {
        const items = await search("upload", makeCtx({ isAnonymous: true }));
        const upload = items.find((i) => i.id === "actions:upload");
        expect(upload).toBeDefined();
        expect(upload?.to).toBe("/upload");
    });

    it("hides login-only actions from anonymous users", async () => {
        const loggedIn = await search("history", makeCtx());
        expect(loggedIn.some((i) => i.id === "actions:new-history")).toBe(true);

        const anonymous = await search("history", makeCtx({ isAnonymous: true }));
        expect(anonymous.some((i) => i.id === "actions:new-history")).toBe(false);
    });

    it("routes workflow creation and import", async () => {
        const create = (await search("create workflow", makeCtx())).find((i) => i.id === "actions:create-workflow");
        expect(create?.to).toBe("/workflows/create");

        const importItem = (await search("import workflow", makeCtx())).find((i) => i.id === "actions:import-workflow");
        expect(importItem?.to).toBe("/workflows/import");
    });
});
