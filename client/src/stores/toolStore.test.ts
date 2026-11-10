import axios from "axios";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { type Tool, useToolStore } from "./toolStore";

vi.mock("axios", () => ({
    default: {
        get: vi.fn(),
    },
}));

vi.mock("@/components/ToolsList/utilities", () => ({
    parseHelpForSummary: vi.fn(() => ""),
}));

describe("toolStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        vi.mocked(axios.get).mockReset();
    });

    it("retains the tag catalog when fetched before tools and attaches tags when tools arrive", async () => {
        vi.mocked(axios.get).mockResolvedValue({ data: { fastqc: ["Quality Control"] } });
        const store = useToolStore();
        await store.fetchToolTagsMapping();
        expect(store.toolTagsById).toEqual({ fastqc: ["Quality Control"] });
        store.saveAllTools([{ id: "fastqc", name: "FastQC" } as Tool]);
        expect(store.toolsById.fastqc?.tool_tags).toEqual(["Quality Control"]);
    });

    it("removes deleted categories from decorated tools and tag names on refresh", async () => {
        const store = useToolStore();
        store.saveAllTools([{ id: "fastqc", name: "FastQC" } as Tool]);
        vi.mocked(axios.get).mockResolvedValueOnce({ data: { fastqc: ["Old category"] } });
        await store.fetchToolTagsMapping();
        expect(store.toolTagNames).toEqual(["Old category"]);
        vi.mocked(axios.get).mockResolvedValueOnce({ data: {} });
        await store.fetchToolTagsMapping(true);
        expect(store.toolTagsById).toEqual({});
        expect(store.toolsById.fastqc?.tool_tags).toEqual([]);
        expect(store.getToolForId("fastqc")?.tool_tags).toEqual([]);
        expect(store.toolTagNames).toEqual([]);
    });

    it("shares pending mapping requests and preserves the catalog when tools load later", async () => {
        const store = useToolStore();
        vi.mocked(axios.get).mockResolvedValue({ data: { fastqc: ["Quality Control"] } });
        await Promise.all([store.fetchToolTagsMapping(), store.fetchToolTagsMapping()]);
        expect(axios.get).toHaveBeenCalledTimes(1);
        store.saveAllTools([{ id: "fastqc", name: "FastQC" } as Tool]);
        store.saveToolForId("fastqc", { id: "fastqc", name: "Updated FastQC" } as Tool);
        await store.fetchToolTagsMapping();
        expect(axios.get).toHaveBeenCalledTimes(1);
        expect(store.toolTagsLoaded).toBe(true);
        expect(store.toolsById.fastqc?.tool_tags).toEqual(["Quality Control"]);
        expect(store.toolsById.fastqc?.name).toBe("Updated FastQC");
    });

    it("keeps decorated tools stable when an unrelated tool is saved", async () => {
        vi.mocked(axios.get).mockResolvedValue({ data: { fastqc: ["Quality Control"] } });
        const store = useToolStore();
        store.saveAllTools([{ id: "fastqc", name: "FastQC" } as Tool, { id: "cat1", name: "Concatenate" } as Tool]);
        await store.fetchToolTagsMapping();
        const fastqc = store.toolsById.fastqc;
        const cat1 = store.toolsById.cat1;
        store.saveToolForId("cat1", { id: "cat1", name: "Concatenate datasets" } as Tool);
        expect(store.toolsById.fastqc).toBe(fastqc);
        expect(store.toolsById.cat1).not.toBe(cat1);
        expect(store.toolsById.cat1?.name).toBe("Concatenate datasets");
        expect(store.toolsById.cat1?.tool_tags).toEqual([]);
    });

    it("caches tool help format from the build response", async () => {
        vi.mocked(axios.get).mockResolvedValue({
            data: {
                help: "**Important** tool help",
                help_format: "markdown",
            },
        });
        const store = useToolStore();

        await store.fetchHelpForId("test-tool");

        expect(store.helpDataCached["test-tool"]).toMatchObject({
            help: "**Important** tool help",
            helpFormat: "markdown",
        });
    });

    it("settles a failed help request and retries it later", async () => {
        const error = new Error("request failed");
        vi.spyOn(console, "error").mockImplementation(() => {});
        vi.mocked(axios.get)
            .mockRejectedValueOnce(error)
            .mockResolvedValueOnce({ data: { help: "Recovered help", help_format: "markdown" } });
        const store = useToolStore();

        await store.fetchHelpForId("test-tool");
        expect(store.helpDataCached["test-tool"]).toEqual({ help: "", failed: true });

        await store.fetchHelpForId("test-tool");
        expect(axios.get).toHaveBeenCalledTimes(2);
        expect(store.helpDataCached["test-tool"]).toMatchObject({ help: "Recovered help" });
    });

    it("does not resolve an uncached query through the prototype chain", () => {
        const store = useToolStore();
        store.saveToolForId("fastqc", { id: "fastqc", name: "FastQC" } as Tool);

        expect(store.getToolsById("constructor")).toEqual({});
    });
});
