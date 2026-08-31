import axios from "axios";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import type { PaletteContext } from "../types";
import { PALETTE_SCOPES } from "./scopes";
import { toolsProvider } from "./tools";

vi.mock("axios", () => ({
    default: {
        get: vi.fn(),
    },
}));

vi.mock("@/components/ToolsList/utilities", () => ({
    parseHelpForSummary: vi.fn(() => ""),
}));

const FASTQC = {
    id: "fastqc_id",
    name: "FastQC",
    description: "Read quality reports",
    model_class: "Tool",
    panel_section_name: "FASTQ Quality Control",
};

const BOWTIE = {
    id: "bowtie_id",
    name: "Bowtie2",
    description: "Map reads against a reference genome",
    model_class: "Tool",
    panel_section_name: "Mapping",
};

const ALL_TOOLS = [FASTQC, BOWTIE];

const TOOLS_SCOPE = PALETTE_SCOPES.find((scope) => scope.key === "t")!;

function makeCtx(): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAdmin: false, isAnonymous: false };
}

/** Bulk `/api/tools` returns the toolbox, a `q` search returns matching ids */
function mockToolsApi(searchResult: string[] = [FASTQC.id]) {
    vi.mocked(axios.get).mockImplementation(async (_url: string, config?: { params?: Record<string, unknown> }) => {
        if (config?.params?.q) {
            return { data: searchResult };
        }
        return { data: ALL_TOOLS };
    });
}

/** Calls carrying a `q` param, i.e. actual backend searches */
function backendSearches() {
    return vi
        .mocked(axios.get)
        .mock.calls.filter(([, config]) => Boolean((config as { params?: Record<string, unknown> })?.params?.q));
}

async function hydrateToolStore() {
    const toolStore = useToolStore();
    await toolStore.fetchTools();
    return toolStore;
}

describe("toolsProvider", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(axios.get).mockReset();
    });

    it("searches the backend and maps matches to palette items", async () => {
        mockToolsApi();
        const items = await toolsProvider.search("fastqc", makeCtx());
        const fastqc = items.find((i) => i.id === "tools:fastqc_id");
        expect(fastqc).toBeDefined();
        expect(fastqc?.title).toBe("FastQC");
        expect(fastqc?.subtitle).toContain("Read quality reports");
        expect(fastqc?.to).toBe("/?tool_id=fastqc_id&version=latest");
    });

    it("answers one and two character queries from the store, without a backend search", async () => {
        mockToolsApi();
        await hydrateToolStore();
        vi.mocked(axios.get).mockClear();

        const byName = await toolsProvider.search("bo", makeCtx());
        expect(byName.map((i) => i.id)).toEqual(["tools:bowtie_id"]);

        const byDescription = await toolsProvider.search("ge", makeCtx());
        expect(byDescription.map((i) => i.id)).toEqual(["tools:bowtie_id"]);

        expect(backendSearches()).toEqual([]);
    });

    it("hydrates the store before matching a short query locally", async () => {
        mockToolsApi();
        const items = await toolsProvider.search("fa", makeCtx());
        expect(items.map((i) => i.id)).toEqual(["tools:fastqc_id"]);
        expect(backendSearches()).toEqual([]);
    });

    it("lists recently used tools for an empty query", async () => {
        mockToolsApi();
        await hydrateToolStore();
        const userStore = useUserStore();
        userStore.recentTools = [FASTQC.id, "not_loaded_tool"];

        const items = toolsProvider.emptyQueryItems?.(makeCtx()) ?? [];
        expect(items.map((i) => i.id)).toEqual(["tools:fastqc_id"]);
    });

    describe("searchScoped", () => {
        beforeEach(() => {
            mockToolsApi();
        });

        it("shows favorites and recent tools only for an empty query", async () => {
            const userStore = useUserStore();
            userStore.currentPreferences = { favorites: { tools: [FASTQC.id] } };
            userStore.recentTools = [BOWTIE.id];

            const sections = (await toolsProvider.searchScoped?.(TOOLS_SCOPE, "", makeCtx())) ?? [];
            expect(sections.map((s) => s.id)).toEqual(["favorites", "recent"]);
            expect(sections[0]?.items.map((i) => i.id)).toEqual(["tools:fastqc_id"]);
            expect(sections[1]?.items.map((i) => i.id)).toEqual(["tools:bowtie_id"]);
            expect(backendSearches()).toEqual([]);
        });

        it("keeps a favorite out of the recent section", async () => {
            const userStore = useUserStore();
            userStore.currentPreferences = { favorites: { tools: [FASTQC.id] } };
            userStore.recentTools = [FASTQC.id];

            const sections = (await toolsProvider.searchScoped?.(TOOLS_SCOPE, "", makeCtx())) ?? [];
            expect(sections.map((s) => s.id)).toEqual(["favorites"]);
        });

        it("filters the top sections by the query and appends the remaining results", async () => {
            const userStore = useUserStore();
            userStore.currentPreferences = { favorites: { tools: [FASTQC.id] } };
            userStore.recentTools = [BOWTIE.id];
            mockToolsApi([FASTQC.id, BOWTIE.id]);

            const sections = (await toolsProvider.searchScoped?.(TOOLS_SCOPE, "quality", makeCtx())) ?? [];
            // "quality" matches the favorite but not the recent tool
            expect(sections.map((s) => s.id)).toEqual(["favorites", "results"]);
            expect(sections[0]?.items.map((i) => i.id)).toEqual(["tools:fastqc_id"]);
            // the favorite is not repeated in the results section
            expect(sections[1]?.items.map((i) => i.id)).toEqual(["tools:bowtie_id"]);
        });

        it("matches short queries locally in the results section too", async () => {
            const userStore = useUserStore();
            userStore.recentTools = [];

            const sections = (await toolsProvider.searchScoped?.(TOOLS_SCOPE, "bo", makeCtx())) ?? [];
            expect(sections.map((s) => s.id)).toEqual(["results"]);
            expect(sections[0]?.items.map((i) => i.id)).toEqual(["tools:bowtie_id"]);
            expect(backendSearches()).toEqual([]);
        });

        it("returns no sections when nothing matches", async () => {
            const sections = (await toolsProvider.searchScoped?.(TOOLS_SCOPE, "zz", makeCtx())) ?? [];
            expect(sections).toEqual([]);
        });
    });
});

describe("prototype-colliding queries", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(axios.get).mockReset();
    });

    it("fetches and returns results for a query that collides with Object.prototype", async () => {
        mockToolsApi([]);
        const items = await toolsProvider.search("constructor", makeCtx());
        expect(items).toEqual([]);
        // the prototype's `constructor` must not pass as a cached search result
        expect(backendSearches().length).toBe(1);
    });
});
