import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

const { server, http } = useServerMock();

const DATATYPES = [
    {
        extension: "bed",
        description: "BED format",
        description_url: null,
        composite_files: null,
        upload_warning: null,
    },
];
const YAML_TERM = "galaxy.invocations.states.scheduled";
const DATATYPE_TERM = "galaxy.datatypes.extensions.bed";

// Upload utils cache datatypes at module scope, so reload all modules for each test.
async function setup() {
    const { createPinia, setActivePinia } = await import("pinia");
    setActivePinia(createPinia());
    return await import("./helpTermsStore");
}

describe("useHelpForTerm", () => {
    let datatypesRequests: number;
    let failNext: number;

    beforeEach(() => {
        vi.resetModules();
        datatypesRequests = 0;
        failNext = 0;
        server.use(
            http.get("/api/datatypes", ({ response }) => {
                datatypesRequests++;
                if (failNext > 0) {
                    failNext--;
                    return response.untyped(
                        HttpResponse.json({ err_msg: "unavailable", err_code: 0 }, { status: 500 }),
                    );
                }
                return response.untyped(HttpResponse.json(DATATYPES));
            }),
        );
    });

    it("does not load datatypes for YAML terms", async () => {
        const { useHelpForTerm } = await setup();
        const helps = Array.from({ length: 10 }, () => useHelpForTerm(ref(YAML_TERM)));
        for (const { loading, hasHelp, help } of helps) {
            expect(loading.value).toBe(false);
            expect(hasHelp.value).toBe(true);
            expect(help.value).toContain("scheduled");
        }
        await flushPromises();
        expect(datatypesRequests).toBe(0);
    });

    it("loads datatypes once for many concurrent datatype terms", async () => {
        const { useHelpForTerm } = await setup();
        const helps = Array.from({ length: 10 }, () => useHelpForTerm(ref(DATATYPE_TERM)));
        expect(helps[0]!.loading.value).toBe(true);
        await vi.waitFor(() => expect(helps[0]!.loading.value).toBe(false));
        await flushPromises();
        expect(datatypesRequests).toBe(1);
        for (const { loading, hasHelp, help } of helps) {
            expect(loading.value).toBe(false);
            expect(hasHelp.value).toBe(true);
            expect(help.value).toBe("BED format");
        }
    });

    it("loads datatypes when the term changes to a datatype term", async () => {
        const { useHelpForTerm } = await setup();
        const term = ref(YAML_TERM);
        const { loading, help } = useHelpForTerm(term);
        await flushPromises();
        expect(datatypesRequests).toBe(0);

        term.value = DATATYPE_TERM;
        await vi.waitFor(() => expect(loading.value).toBe(false));
        expect(help.value).toBe("BED format");
        expect(datatypesRequests).toBe(1);
    });

    it("retries loading datatypes for a later term after a failed load", async () => {
        failNext = 1;
        const { useHelpForTerm } = await setup();
        const failed = useHelpForTerm(ref(DATATYPE_TERM));
        await vi.waitFor(() => expect(failed.loading.value).toBe(false));
        expect(failed.hasHelp.value).toBe(false);
        expect(datatypesRequests).toBe(1);

        const retried = useHelpForTerm(ref(DATATYPE_TERM));
        await vi.waitFor(() => expect(retried.help.value).toBe("BED format"));
        expect(retried.loading.value).toBe(false);
        expect(datatypesRequests).toBe(2);
    });
});
