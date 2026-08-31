import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type * as HistoriesApi from "@/api/histories";
import { createNewHistory } from "@/api/histories";
import { uploadMethodRegistry } from "@/components/Panels/Upload/uploadMethodRegistry";
import { useHistoryStore } from "@/stores/historyStore";

import type { PaletteContext, PaletteItem } from "../types";
import { actionsProvider } from "./actions";

vi.mock("@/api/histories", async (importOriginal) => ({
    ...(await importOriginal<typeof HistoriesApi>()),
    createNewHistory: vi.fn().mockResolvedValue({ id: "hist-1" }),
}));

function makeCtx(overrides: Partial<PaletteContext> = {}): PaletteContext {
    return {
        canUseUnprivilegedTools: false,
        config: {},
        isAdmin: false,
        isAnonymous: false,
        // the palette resolves these with `useFilteredUploadMethods`, which
        // already dropped whatever this user may not run
        uploadMethods: Object.values(uploadMethodRegistry).filter((method) => !method.requiresLogin),
        ...overrides,
    };
}

async function search(query: string, ctx: PaletteContext) {
    return actionsProvider.search(query, ctx);
}

async function action(id: string, ctx: PaletteContext = makeCtx()): Promise<PaletteItem> {
    const found = (actionsProvider.emptyQueryItems?.(ctx) ?? []).find((item) => item.id === id);
    if (!found) {
        throw new Error(`action ${id} is not available`);
    }
    return found;
}

async function argumentItems(actionId: string, argQuery: string, ctx: PaletteContext = makeCtx()) {
    const item = await action(actionId, ctx);
    return item.argumentMode ? await item.argumentMode.getItems(argQuery, ctx) : [];
}

describe("actionsProvider", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.clearAllMocks();
        vi.mocked(createNewHistory).mockResolvedValue({ id: "hist-1" } as never);
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

    it("offers the upload methods as the upload argument", async () => {
        const items = await argumentItems("actions:upload", "paste");

        expect(items.map((item) => item.to)).toContain("/upload/paste-content");
        expect(items.every((item) => item.to?.startsWith("/upload/"))).toBe(true);
        // methods the user cannot use are dropped, not shown disabled
        expect(items.some((item) => item.id === "actions:upload:import-history")).toBe(false);
    });

    it("turns the typed name into the history creation row", async () => {
        expect(await argumentItems("actions:new-history", "  ")).toEqual([]);

        const [item] = await argumentItems("actions:new-history", " RNA run ");
        expect(item?.title).toBe("Create history named 'RNA run'");

        const historyStore = useHistoryStore();
        const setCurrentHistory = vi.spyOn(historyStore, "setCurrentHistory").mockResolvedValue(undefined);
        item?.handler?.(makeCtx());
        await vi.waitFor(() => expect(setCurrentHistory).toHaveBeenCalledWith("hist-1"));
        expect(createNewHistory).toHaveBeenCalledWith("RNA run");
    });

    it("routes workflow creation and import", async () => {
        const create = (await search("create workflow", makeCtx())).find((i) => i.id === "actions:create-workflow");
        expect(create?.to).toBe("/workflows/create");

        const importItem = (await search("import workflow", makeCtx())).find((i) => i.id === "actions:import-workflow");
        expect(importItem?.to).toBe("/workflows/import");
    });
});
