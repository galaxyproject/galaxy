import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

const { server, http } = useServerMock();

const DATATYPES = [
    { extension: "txt", description: "Text", description_url: null, composite_files: null, upload_warning: null },
    { extension: "bed", description: "BED", description_url: null, composite_files: null, upload_warning: null },
];
const GENOMES = [
    ["Human hg38", "hg38"],
    ["Unspecified", "?"],
];

// The module caches results at module scope, so reload it for each test.
async function loadUtils() {
    return await import("./utils");
}

describe("Upload utils caching", () => {
    let datatypesRequests: number;
    let dbKeysRequests: number;

    beforeEach(() => {
        vi.resetModules();
        datatypesRequests = 0;
        dbKeysRequests = 0;
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                datatypesRequests++;
                return response.untyped(HttpResponse.json(DATATYPES));
            }),
            http.get("/api/genomes", ({ response }) => {
                dbKeysRequests++;
                return response.untyped(HttpResponse.json(GENOMES));
            }),
        );
    });

    it("shares one datatypes request between concurrent callers", async () => {
        const { getUploadDatatypes, AUTO_EXTENSION } = await loadUtils();
        const results = await Promise.all(Array.from({ length: 10 }, () => getUploadDatatypes(false, AUTO_EXTENSION)));
        expect(datatypesRequests).toBe(1);
        for (const result of results) {
            expect(result.map((e: { id: string }) => e.id)).toEqual(["auto", "bed", "txt"]);
        }
        await getUploadDatatypes(true, AUTO_EXTENSION);
        expect(datatypesRequests).toBe(1);
    });

    it("refetches datatypes after a failed request", async () => {
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                datatypesRequests++;
                return response.untyped(HttpResponse.json({ err_code: 503, err_msg: "Unavailable" }, { status: 503 }));
            }),
        );
        const { getUploadDatatypes, AUTO_EXTENSION } = await loadUtils();
        const failures = await Promise.allSettled([
            getUploadDatatypes(true, AUTO_EXTENSION),
            getUploadDatatypes(true, AUTO_EXTENSION),
        ]);
        expect(failures.map((f) => f.status)).toEqual(["rejected", "rejected"]);
        expect(datatypesRequests).toBe(1);

        server.resetHandlers();
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                datatypesRequests++;
                return response.untyped(HttpResponse.json(DATATYPES));
            }),
        );
        const result = await getUploadDatatypes(true, AUTO_EXTENSION);
        expect(result.map((e: { id: string }) => e.id)).toEqual(["bed", "txt"]);
        expect(datatypesRequests).toBe(2);
    });

    it("shares one genomes request between concurrent callers", async () => {
        const { getUploadDbKeys } = await loadUtils();
        const results = await Promise.all(Array.from({ length: 10 }, () => getUploadDbKeys("?")));
        expect(dbKeysRequests).toBe(1);
        for (const result of results) {
            expect(result.map((e: { id: string }) => e.id)).toEqual(["?", "hg38"]);
        }
    });

    it("refetches genomes after a failed request", async () => {
        server.use(
            http.get("/api/genomes", ({ response }) => {
                dbKeysRequests++;
                return response.untyped(HttpResponse.json({ err_code: 500, err_msg: "Error" }, { status: 500 }));
            }),
        );
        const { getUploadDbKeys } = await loadUtils();
        await expect(getUploadDbKeys("?")).rejects.toBeTruthy();
        expect(dbKeysRequests).toBe(1);

        server.resetHandlers();
        server.use(
            http.get("/api/genomes", ({ response }) => {
                dbKeysRequests++;
                return response.untyped(HttpResponse.json(GENOMES));
            }),
        );
        const result = await getUploadDbKeys("?");
        expect(result).toHaveLength(2);
        expect(dbKeysRequests).toBe(2);
    });
});
