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
    const requestedUrls: URL[] = [];

    server.use(
        http.get("/api/workflows", ({ request, response }: any) => {
            requestedUrls.push(new URL(request.url));
            return response(200).json([]);
        }) as any,
    );

    return requestedUrls;
}

describe("workflows API", () => {
    describe("loadWorkflows", () => {
        it("omits show_shared unless it is requested", async () => {
            const requestedUrls = mockWorkflowsIndex();

            await loadWorkflows({ ...DEFAULT_OPTIONS });

            expect(requestedUrls[0]?.searchParams.has("show_shared")).toBe(false);
        });

        it("passes show_shared through when requested", async () => {
            const requestedUrls = mockWorkflowsIndex();

            await loadWorkflows({ ...DEFAULT_OPTIONS, showShared: true, filterText: "is:shared_with_me" });

            expect(requestedUrls[0]?.searchParams.get("show_shared")).toBe("true");
            expect(requestedUrls[0]?.searchParams.get("search")).toBe("is:shared_with_me");
        });
    });
});
