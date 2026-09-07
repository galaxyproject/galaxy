import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type * as HistoriesApi from "@/api/histories";
import { createNewHistory } from "@/api/histories";
import type * as PagesApi from "@/api/pages";
import { createPage } from "@/api/pages";
import type { WorkflowSummary } from "@/api/workflows";
import { loadWorkflows } from "@/api/workflows";
import type { ChatHistoryItem } from "@/components/GalaxyAI/chatTypes";
import { uploadMethodRegistry } from "@/components/Panels/Upload/uploadMethodRegistry";
import { Toast } from "@/composables/toast";
import { useChatStore } from "@/stores/chatStore";
import { useHistoryStore } from "@/stores/historyStore";
import { usePageStore } from "@/stores/pageStore";

import type { PaletteContext, PaletteItem } from "../types";
import { actionsProvider, slugify } from "./actions";

vi.mock("@/api/histories", async (importOriginal) => ({
    ...(await importOriginal<typeof HistoriesApi>()),
    createNewHistory: vi.fn(),
}));

vi.mock("@/api/pages", async (importOriginal) => ({
    ...(await importOriginal<typeof PagesApi>()),
    createPage: vi.fn(),
}));

vi.mock("@/api/workflows", () => ({
    loadWorkflows: vi.fn(),
}));

vi.mock("@/composables/toast", () => ({
    Toast: { error: vi.fn(), success: vi.fn(), info: vi.fn(), warning: vi.fn() },
}));

vi.mock("@/components/Workflow/workflows.services", () => ({
    getWorkflowFull: vi.fn(),
}));

const RNA_SEQ = { id: "wf1", name: "RNA-seq analysis", owner: "me", tags: [] } as unknown as WorkflowSummary;

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
        vi.mocked(createPage).mockResolvedValue({ id: "page-1" } as never);
        vi.mocked(loadWorkflows).mockResolvedValue({ data: [RNA_SEQ], totalMatches: 1 });
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
        const handleTotalCountChange = vi.spyOn(historyStore, "handleTotalCountChange").mockResolvedValue(undefined);
        item?.handler?.(makeCtx());
        await vi.waitFor(() => expect(setCurrentHistory).toHaveBeenCalledWith("hist-1"));
        expect(createNewHistory).toHaveBeenCalledWith("RNA run");
        // the store's own creation refreshes the paginated total, and so must this one
        await vi.waitFor(() => expect(handleTotalCountChange).toHaveBeenCalledWith(1));
    });

    it("reports a failed history creation without touching the total count", async () => {
        vi.mocked(createNewHistory).mockRejectedValueOnce(new Error("nope"));

        const historyStore = useHistoryStore();
        const setCurrentHistory = vi.spyOn(historyStore, "setCurrentHistory").mockResolvedValue(undefined);
        const handleTotalCountChange = vi.spyOn(historyStore, "handleTotalCountChange").mockResolvedValue(undefined);

        const [item] = await argumentItems("actions:new-history", "RNA run");
        item?.handler?.(makeCtx());

        await vi.waitFor(() => expect(Toast.error).toHaveBeenCalled());
        expect(setCurrentHistory).not.toHaveBeenCalled();
        expect(handleTotalCountChange).not.toHaveBeenCalled();
    });

    it("keeps a stale count from looking like a failed history creation", async () => {
        const historyStore = useHistoryStore();
        const setCurrentHistory = vi.spyOn(historyStore, "setCurrentHistory").mockResolvedValue(undefined);
        vi.spyOn(historyStore, "handleTotalCountChange").mockRejectedValue(new Error("count is down"));

        const [item] = await argumentItems("actions:new-history", "RNA run");
        item?.handler?.(makeCtx());

        await vi.waitFor(() => expect(setCurrentHistory).toHaveBeenCalledWith("hist-1"));
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(Toast.error).not.toHaveBeenCalled();
    });

    it("routes workflow creation and import", async () => {
        const create = (await search("create workflow", makeCtx())).find((i) => i.id === "actions:create-workflow");
        expect(create?.to).toBe("/workflows/create");

        const importItem = (await search("import workflow", makeCtx())).find((i) => i.id === "actions:import-workflow");
        expect(importItem?.to).toBe("/workflows/import");
    });

    it("creates a page from the typed title and opens its editor", async () => {
        const createItem = await action("actions:create-page");
        expect(createItem.to).toBe("/pages/create");
        expect(await argumentItems("actions:create-page", "   ")).toEqual([]);

        const navigate = vi.fn();
        const ctx = makeCtx({ navigate });
        const [item] = await argumentItems("actions:create-page", " My New Page ", ctx);
        expect(item?.title).toBe("Create page titled 'My New Page'");

        item?.handler?.(ctx);
        await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith("/pages/editor?id=page-1"));
        expect(createPage).toHaveBeenCalledWith({
            title: "My New Page",
            slug: "my-new-page",
            content_format: "markdown",
        });
    });

    it("seeds the created page into the page store, ahead of the cached ones", async () => {
        vi.mocked(createPage).mockResolvedValue({
            id: "page-1",
            title: "My New Page",
            slug: "my-new-page",
            update_time: "2026-01-02T00:00:00",
        } as never);

        const pageStore = usePageStore();
        // a cache the `r:` scope would otherwise consider complete, so a missing
        // seed would leave the new page invisible until the next unfiltered fetch
        pageStore.savePages("my", [{ id: "page-0", title: "Older page" } as never]);

        const navigate = vi.fn();
        const ctx = makeCtx({ navigate });
        const [item] = await argumentItems("actions:create-page", "My New Page", ctx);
        item?.handler?.(ctx);

        await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith("/pages/editor?id=page-1"));
        expect(pageStore.getPageById("page-1")).toMatchObject({ title: "My New Page" });
        expect(pageStore.getPages("my").map((page) => page.id)).toEqual(["page-1", "page-0"]);
    });

    it("leaves the page store untouched when the creation fails", async () => {
        vi.mocked(createPage).mockRejectedValue(new Error("nope"));

        const pageStore = usePageStore();
        const navigate = vi.fn();
        const ctx = makeCtx({ navigate });
        const [item] = await argumentItems("actions:create-page", "My New Page", ctx);
        item?.handler?.(ctx);

        await vi.waitFor(() => expect(Toast.error).toHaveBeenCalled());
        expect(navigate).not.toHaveBeenCalled();
        expect(pageStore.getPages("my")).toEqual([]);
    });

    it("retries a conflicting page slug once with a suffix", async () => {
        vi.mocked(createPage)
            .mockRejectedValueOnce(new Error("Page identifier must be unique"))
            .mockResolvedValueOnce({ id: "page-2" } as never);

        const navigate = vi.fn();
        const ctx = makeCtx({ navigate });
        const [item] = await argumentItems("actions:create-page", "Lab notes", ctx);
        item?.handler?.(ctx);

        await vi.waitFor(() => expect(navigate).toHaveBeenCalledWith("/pages/editor?id=page-2"));
        expect(createPage).toHaveBeenNthCalledWith(2, expect.objectContaining({ slug: "lab-notes-2" }));
    });

    it("picks the workflow to run as an argument, with no plain enter target", async () => {
        const runWorkflow = await action("actions:run-workflow");
        expect(runWorkflow.to).toBeUndefined();
        expect(runWorkflow.handler).toBeUndefined();
        // nothing useful to do without a workflow, so enter opens the picker too
        expect(runWorkflow.argumentMode?.immediate).toBe(true);

        const items = await argumentItems("actions:run-workflow", "rna");
        expect(items[0]?.title).toBe("RNA-seq analysis");
        expect(items[0]?.to).toBe("/workflows/run?id=wf1");
    });

    it("hides GalaxyAI unless the assistant is configured", async () => {
        const ids = (ctx: PaletteContext) => (actionsProvider.emptyQueryItems?.(ctx) ?? []).map((item) => item.id);
        expect(ids(makeCtx())).not.toContain("actions:galaxy-ai");
        expect(ids(makeCtx({ config: { llm_api_configured: true } }))).toContain("actions:galaxy-ai");
        expect(ids(makeCtx({ config: { llm_api_configured: true }, isAnonymous: true }))).not.toContain(
            "actions:galaxy-ai",
        );
    });

    it("starts a GalaxyAI conversation and seeds one from the typed question", async () => {
        const startNewChat = vi.fn();
        const ctx = makeCtx({ config: { llm_api_configured: true }, startNewChat });
        const galaxyAi = await action("actions:galaxy-ai", ctx);

        galaxyAi.handler?.(ctx);
        expect(startNewChat).toHaveBeenCalledWith(true);

        const chatStore = useChatStore();
        chatStore.chatHistory = [
            { id: "chat-1", query: "How do I filter a fastq file?", response: "Use the filter tool" },
        ] as ChatHistoryItem[];
        const loadHistory = vi.spyOn(chatStore, "loadHistory");

        const items = await argumentItems("actions:galaxy-ai", "filter", ctx);
        expect(items[0]).toMatchObject({ title: "New chat: 'filter'", to: "/galaxyai/new?q=filter" });
        expect(items[1]?.to).toBe("/galaxyai/chat-1");
        // the cache already holds the conversations, so no request is needed
        expect(loadHistory).not.toHaveBeenCalled();
    });

    it("loads the GalaxyAI history into the store and encodes the seeded question", async () => {
        const ctx = makeCtx({ config: { llm_api_configured: true } });
        const chatStore = useChatStore();
        const loadHistory = vi.spyOn(chatStore, "loadHistory").mockResolvedValue(undefined);

        const items = await argumentItems("actions:galaxy-ai", "trim my reads", ctx);
        expect(loadHistory).toHaveBeenCalled();
        expect(items[0]?.to).toBe("/galaxyai/new?q=trim%20my%20reads");
    });
});

describe("slugify", () => {
    it("lowercases, collapses non alphanumeric runs and trims dashes", () => {
        expect(slugify("  My New Page!! ")).toBe("my-new-page");
        expect(slugify("RNA-seq 2026 — draft")).toBe("rna-seq-2026-draft");
    });

    it("falls back for a title without a single usable character", () => {
        expect(slugify("???")).toBe("page");
    });
});
