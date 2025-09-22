import { getFilename, getRequiresDataset, getTestUrls } from "./utilities";

describe("Utility Functions", () => {
    describe("getRequiresDataset and getTestUrls", () => {
        it("return wether the visualization requires a dataset or not", () => {
            expect(getRequiresDataset({})).toEqual(false);
            const plugin = {
                params: { dataset_id: { required: true } },
            };
            expect(getRequiresDataset(plugin)).toEqual(true);
        });

        it("returns empty array when plugin is undefined", () => {
            expect(getTestUrls()).toEqual([]);
        });

        it("returns empty array when plugin has no tests", () => {
            const plugin = {};
            expect(getTestUrls(plugin)).toEqual([]);
        });

        it("returns empty array when no valid dataset_id params", () => {
            const plugin = {
                tests: [{ param: { name: "other_param", value: "http://example.com/file.csv" } }, { param: null }],
            };
            expect(getTestUrls(plugin)).toEqual([]);
        });

        it("returns valid test URLs with extracted filename", () => {
            const plugin = {
                tests: [
                    { param: { name: "dataset_id", value: "http://example.com/data/test1.csv" } },
                    { param: { name: "dataset_id", value: "http://example.com/data/test2.json" } },
                    { param: { name: "other_param", value: "http://example.com/ignore.me" } },
                ],
            };
            expect(getTestUrls(plugin)).toEqual([
                { name: "test1.csv", url: "http://example.com/data/test1.csv" },
                { name: "test2.json", url: "http://example.com/data/test2.json" },
            ]);
        });

        it("handles invalid URLs gracefully", () => {
            const plugin = {
                tests: [{ param: { name: "dataset_id", value: "not-a-url" } }],
            };
            expect(getTestUrls(plugin)).toEqual([]);
        });

        it("handles URLs with multiple dots in filename", () => {
            const plugin = {
                tests: [{ param: { name: "dataset_id", value: "http://example.com/data/archive.tar.gz" } }],
            };
            expect(getTestUrls(plugin)).toEqual([
                { name: "archive.tar.gz", url: "http://example.com/data/archive.tar.gz" },
            ]);
        });
    });

    describe("getFilename", () => {
        it("extracts filename from valid URL", () => {
            expect(getFilename("http://example.com/path/to/file.txt")).toBe("file.txt");
        });

        it("returns empty string for invalid URL", () => {
            expect(getFilename("not-a-url")).toBe("");
        });

        it("handles URLs without path", () => {
            expect(getFilename("http://example.com")).toBe("");
        });

        it("handles URLs with trailing slash", () => {
            expect(getFilename("http://example.com/path/")).toBe("path");
        });
    });
});
