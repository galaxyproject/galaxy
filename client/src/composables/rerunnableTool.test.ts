import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { HttpResponse } from "msw";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, ref } from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import { useRerunnableTool } from "./rerunnableTool";

const { server, http } = useServerMock();

/** The tool store fetches via axios, whose responses need more than a microtask flush. */
function settleRequests() {
    return new Promise((resolve) => setTimeout(resolve, 100));
}

function mountRerunnableTool(toolId: ReturnType<typeof ref<string | undefined>>) {
    let result: ReturnType<typeof useRerunnableTool> | undefined;
    mount(
        defineComponent({
            setup() {
                result = useRerunnableTool(toolId);
                return () => null;
            },
        }),
    );
    return result!;
}

describe("useRerunnableTool", () => {
    beforeEach(() => {
        setActivePinia(createTestingPinia({ createSpy: vi.fn, stubActions: false }));
    });

    it("settles to an error when the tool can't be fetched", async () => {
        server.use(
            http.untyped.get("/api/tools/:tool_id", () =>
                HttpResponse.json({ err_msg: "Tool not found", err_code: 404 }, { status: 404 }),
            ),
        );
        const { loading, error, canRerun } = mountRerunnableTool(ref<string | undefined>("tool_a"));
        expect(loading.value).toBe(true);

        await settleRequests();

        expect(loading.value).toBe(false);
        expect(error.value).toContain("Tool not found");
        expect(canRerun.value).toBe(false);
    });

    /** Fails the first `tool_a` request once `failToolA` is called; every other request stays pending. */
    function mockDelayedToolAFailure() {
        const fetches = { toolA: 0, failToolA: () => {} };
        server.use(
            http.untyped.get("/api/tools/:tool_id", async ({ params }) => {
                if (params.tool_id === "tool_a" && ++fetches.toolA === 1) {
                    await new Promise<void>((resolve) => (fetches.failToolA = resolve));
                    return HttpResponse.json({ err_msg: "Tool not found", err_code: 404 }, { status: 404 });
                }
                return new Promise<never>(() => {});
            }),
        );
        return fetches;
    }

    it("ignores a failure from a fetch for a tool it has since switched away from", async () => {
        const fetches = mockDelayedToolAFailure();
        const toolId = ref<string | undefined>("tool_a");
        const { loading, error } = mountRerunnableTool(toolId);
        await settleRequests();
        toolId.value = "tool_b";
        await settleRequests();

        fetches.failToolA();
        await settleRequests();

        expect(error.value).toBeNull();
        expect(loading.value).toBe(true);
    });

    it("shares the in-flight request when switching back to the same tool, and reports its failure", async () => {
        const fetches = mockDelayedToolAFailure();
        const toolId = ref<string | undefined>("tool_a");
        const { loading, error } = mountRerunnableTool(toolId);
        await settleRequests();
        toolId.value = "tool_b";
        await settleRequests();
        toolId.value = "tool_a";
        await settleRequests();

        fetches.failToolA();
        await settleRequests();

        expect(fetches.toolA).toBe(1);
        expect(error.value).toContain("Tool not found");
        expect(loading.value).toBe(false);
    });
});
