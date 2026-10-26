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

    it("shares one in-flight tool request between concurrent callers", async () => {
        vi.mocked(axios.get).mockResolvedValue({ data: { id: "cat1", name: "Concatenate" } });
        const store = useToolStore();

        await Promise.all([store.fetchToolForId("cat1"), store.fetchToolForId("cat1")]);
        await store.fetchToolForId("cat1");

        expect(axios.get).toHaveBeenCalledTimes(1);
        expect(store.getToolForId("cat1")).toMatchObject({ name: "Concatenate" });
    });

    it("rejects every waiting caller on a failed tool request and retries it later", async () => {
        vi.mocked(axios.get)
            .mockRejectedValueOnce(new Error("request failed"))
            .mockResolvedValueOnce({ data: { id: "cat1", name: "Concatenate" } });
        const store = useToolStore();

        const results = await Promise.allSettled([store.fetchToolForId("cat1"), store.fetchToolForId("cat1")]);
        expect(results.map((r) => r.status)).toEqual(["rejected", "rejected"]);

        await store.fetchToolForId("cat1");
        expect(axios.get).toHaveBeenCalledTimes(2);
        expect(store.getToolForId("cat1")).toMatchObject({ name: "Concatenate" });
    });

    it("does not resolve an uncached query through the prototype chain", () => {
        const store = useToolStore();
        store.saveToolForId("fastqc", { id: "fastqc", name: "FastQC" } as Tool);

        expect(store.getToolsById("constructor")).toEqual({});
    });

    it("fetches the full tool list once even when a single tool was loaded first", async () => {
        const fastqc = { id: "fastqc", name: "FastQC" } as Tool;
        const igv = { id: "igv", name: "IGV", model_class: "InteractiveTool" } as Tool;
        vi.mocked(axios.get)
            .mockResolvedValueOnce({ data: fastqc })
            .mockResolvedValueOnce({ data: [fastqc, igv] });
        const store = useToolStore();

        await store.fetchToolForId("fastqc");
        await store.fetchTools();
        await store.fetchTools();

        expect(axios.get).toHaveBeenCalledTimes(2);
        expect(axios.get).toHaveBeenLastCalledWith(expect.stringContaining("api/tools"), {
            params: { in_panel: false },
        });
        expect(Object.keys(store.toolsById)).toEqual(["fastqc", "igv"]);
        expect(store.getInteractiveTools()).toEqual([igv]);
    });

    it("shares one bulk tool request between concurrent callers", async () => {
        const fastqc = { id: "fastqc", name: "FastQC" } as Tool;
        vi.mocked(axios.get).mockResolvedValue({ data: [fastqc] });
        const store = useToolStore();

        await Promise.all([store.fetchTools(), store.fetchTools()]);

        expect(axios.get).toHaveBeenCalledTimes(1);
        expect(store.getToolForId("fastqc")).toEqual(fastqc);
        expect(store.loading).toBe(false);
    });

    it("rejects every concurrent caller and retries after a failed bulk load", async () => {
        const fastqc = { id: "fastqc", name: "FastQC" } as Tool;
        vi.mocked(axios.get)
            .mockRejectedValueOnce(new Error("Toolbox unavailable"))
            .mockResolvedValueOnce({ data: [fastqc] });
        const store = useToolStore();

        const results = await Promise.allSettled([store.fetchTools(), store.fetchTools()]);
        expect(results.map((result) => result.status)).toEqual(["rejected", "rejected"]);
        expect(axios.get).toHaveBeenCalledTimes(1);

        await store.fetchTools();
        expect(axios.get).toHaveBeenCalledTimes(2);
        expect(store.getToolForId("fastqc")).toEqual(fastqc);
    });

    it("keeps a single tool missing from the bulk list after the bulk load", async () => {
        const converter = { id: "CONVERTER_bam_to_bigwig_0", name: "Convert BAM to BigWig", hidden: true } as Tool;
        const fastqc = { id: "fastqc", name: "FastQC" } as Tool;
        vi.mocked(axios.get)
            .mockResolvedValueOnce({ data: converter })
            .mockResolvedValueOnce({ data: [fastqc] });
        const store = useToolStore();

        await store.fetchToolForId(converter.id);
        await store.fetchTools();

        expect(store.getToolForId(converter.id)).toEqual(converter);
        expect(store.getToolForId("fastqc")).toEqual(fastqc);
    });

    it("finds tool ids by name, partially by default and exactly (case-insensitive) when `exact` is true", () => {
        const store = useToolStore();
        store.saveAllTools([
            { id: "cut1", name: "Cut" },
            { id: "adv_cut1", name: "Advanced Cut" },
        ] as unknown as Tool[]);

        expect(store.getToolIdsByName("cut").sort()).toEqual(["adv_cut1", "cut1"]);
        expect(store.getToolIdsByName("CUT", true)).toEqual(["cut1"]);
    });

    it("still fetches the full tool list even if some tools were already fetched one at a time", async () => {
        vi.mocked(axios.get)
            .mockResolvedValueOnce({ data: { id: "cat1", name: "Concatenate" } })
            .mockResolvedValueOnce({
                data: [
                    { id: "cat1", name: "Concatenate" },
                    { id: "random_lines1", name: "Select random lines" },
                ],
            });
        const store = useToolStore();

        // A single tool landing in `toolsById` (e.g. a job card's own rerunnable-tool check)
        // must not look like the full list is already loaded.
        await store.fetchToolForId("cat1");
        await store.fetchTools();

        expect(axios.get).toHaveBeenCalledWith(expect.stringContaining("api/tools"), {
            params: { in_panel: false },
        });
        expect(store.getToolIdsByName("random lines")).toEqual(["random_lines1"]);
    });

    it("does not re-fetch the full tool list once it's already loaded", async () => {
        vi.mocked(axios.get).mockResolvedValue({ data: [{ id: "cat1", name: "Concatenate" }] });
        const store = useToolStore();

        await store.fetchTools();
        await store.fetchTools();

        expect(axios.get).toHaveBeenCalledTimes(1);
    });
});
