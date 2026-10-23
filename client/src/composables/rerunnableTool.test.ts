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

    it("ignores a failure from an earlier fetch after switching away and back to the same tool", async () => {
        let toolAFetches = 0;
        let failFirstFetch: () => void = () => {};
        server.use(
            http.untyped.get("/api/tools/:tool_id", async ({ params }) => {
                if (params.tool_id === "tool_a" && ++toolAFetches === 1) {
                    await new Promise<void>((resolve) => (failFirstFetch = resolve));
                    return HttpResponse.json({ err_msg: "Tool not found", err_code: 404 }, { status: 404 });
                }
                // Every other fetch stays pending
                return new Promise<never>(() => {});
            }),
        );
        const toolId = ref<string | undefined>("tool_a");
        const { loading, error } = mountRerunnableTool(toolId);
        await settleRequests();
        toolId.value = "tool_b";
        await settleRequests();
        toolId.value = "tool_a";
        await settleRequests();

        failFirstFetch();
        await settleRequests();

        expect(error.value).toBeNull();
        expect(loading.value).toBe(true);
    });
});
