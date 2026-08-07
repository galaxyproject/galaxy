import axios from "axios";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import type { PaletteContext } from "../types";
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

function makeCtx(): PaletteContext {
    return { canUseUnprivilegedTools: false, config: {}, isAdmin: false, isAnonymous: false };
}

function mockToolsApi() {
    vi.mocked(axios.get).mockImplementation(async (_url: string, config?: { params?: Record<string, unknown> }) => {
        if (config?.params?.q) {
            return { data: [FASTQC.id] };
        }
        return { data: [FASTQC] };
    });
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

    it("skips the backend below the minimum query length", async () => {
        mockToolsApi();
        const items = await toolsProvider.search("fa", makeCtx());
        expect(items).toEqual([]);
        expect(axios.get).not.toHaveBeenCalled();
    });

    it("lists recently used tools for an empty query", async () => {
        mockToolsApi();
        const toolStore = useToolStore();
        await toolStore.fetchTools();
        const userStore = useUserStore();
        userStore.recentTools = [FASTQC.id, "not_loaded_tool"];

        const items = toolsProvider.emptyQueryItems?.(makeCtx()) ?? [];
        expect(items.map((i) => i.id)).toEqual(["tools:fastqc_id"]);
    });
});
