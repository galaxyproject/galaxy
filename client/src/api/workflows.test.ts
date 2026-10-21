import { describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import { loadWorkflows } from "./workflows";

const { server, http } = useServerMock();

const DEFAULT_OPTIONS = {
    sortBy: "update_time",
    sortDesc: true,
    limit: 20,
    offset: 0,
    filterText: "",
    showPublished: false,
    skipStepCounts: true,
} as const;

function mockWorkflowsIndex() {
    const queries: Record<string, string>[] = [];

    server.use(
        http.get("/api/workflows", ({ request, response }) => {
            queries.push(Object.fromEntries(new URL(request.url).searchParams));
            return response(200).json([]);
        }),
    );

    return queries;
}

describe("workflows API", () => {
    describe("loadWorkflows", () => {
        it("omits show_shared unless it is requested", async () => {
            const queries = mockWorkflowsIndex();

            await loadWorkflows({ ...DEFAULT_OPTIONS });

            expect(queries).toHaveLength(1);
            expect(queries[0]).not.toHaveProperty("show_shared");
        });

        it("passes show_shared through when requested", async () => {
            const queries = mockWorkflowsIndex();

            await loadWorkflows({ ...DEFAULT_OPTIONS, showShared: true, filterText: "is:shared_with_me" });

            expect(queries).toHaveLength(1);
            expect(queries[0]).toHaveProperty("show_shared", "true");
            expect(queries[0]).toHaveProperty("search", "is:shared_with_me");
        });
    });
});
