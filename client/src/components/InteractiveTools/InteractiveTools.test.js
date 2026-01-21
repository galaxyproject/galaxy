import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { useInteractiveToolsStore } from "@/stores/interactiveToolsStore";

import testInteractiveToolsResponse from "./testData/testInteractiveToolsResponse.json";

import InteractiveTools from "./InteractiveTools.vue";

// Mock the rethrowSimple function to prevent test failures
vi.mock("@/utils/simple-error", () => ({
    rethrowSimple: vi.fn(),
    errorMessageAsString: vi.fn((error) => error.message),
}));

const { server, http } = useServerMock();

describe("InteractiveTools/InteractiveTools.vue", () => {
    const localVue = getLocalVue();
    localVue.use(PiniaVuePlugin);
    let wrapper;
    let testPinia;
    let deleteRequests = [];

    beforeEach(async () => {
        deleteRequests = [];
        // Set up the GET response for entry points - use a copy to avoid modifications between tests
        const testData = JSON.parse(JSON.stringify(testInteractiveToolsResponse));
        server.use(
            http.untyped.get("/api/entry_points", () => {
                return HttpResponse.json(testData);
            }),
        );

        testPinia = createTestingPinia({
            createSpy: vi.fn,
            initialState: {
                entryPointStore: {
                    entryPoints: testData,
                },
                interactiveToolsStore: {
                    messages: [],
                    activeTools: testData,
                },
            },
            stubActions: false,
        });
        setActivePinia(testPinia);

        wrapper = mount(InteractiveTools, {
            localVue,
            pinia: testPinia,
        });

        // Wait for any async operations to complete
        await flushPromises();
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it("renders table with interactive tools", async () => {
        expect(wrapper.get("#interactive-tool-table").exists()).toBeTruthy();
        // Each entry has 2 links: one to open inline and one to open in new tab
        expect(wrapper.findAll("td > a").length).toBe(4);
    });

    it("displays interactive tool information correctly", async () => {
        const firstTool = testInteractiveToolsResponse[0];
        const toolName = wrapper.find(`#link-${firstTool.id}`);
        expect(toolName.text()).toContain(firstTool.name);

        // Check if the external link is present
        const externalLink = wrapper.find(`#external-link-${firstTool.id}`);
        expect(externalLink.exists()).toBeTruthy();
        expect(externalLink.attributes("href")).toBe(firstTool.target);
        expect(externalLink.attributes("target")).toBe("_blank");
    });

    it("removes the interactive tool when it is gone from store", async () => {
        const firstTool = testInteractiveToolsResponse[0];

        function checkIfExists(tag, id) {
            return wrapper.find(tag + id).exists();
        }

        expect(checkIfExists("#link-", firstTool.id)).toBeTruthy();

        // drop the tested tool from store
        const store = useEntryPointStore();
        await store.entryPoints.splice(0, 1);

        expect(checkIfExists("#link-", firstTool.id)).toBeFalsy();
    });

    it("sends a delete request after the stop button is pressed", async () => {
        const firstTool = testInteractiveToolsResponse[0];
        const toolId = firstTool.id;

        server.use(
            http.untyped.delete(/\/api\/entry_points\/.*/, ({ request }) => {
                deleteRequests.push({ url: request.url });
                return HttpResponse.json({ status: "ok", message: "ok" });
            }),
        );
        await wrapper.get(`#stop-${toolId}`).trigger("click");
        await flushPromises();

        expect(deleteRequests.length).toBe(1);
        expect(deleteRequests[0].url.includes(toolId)).toBeTruthy();
    });

    it("shows an error message if the tool deletion fails", async () => {
        const firstTool = testInteractiveToolsResponse[0];
        const toolId = firstTool.id;
        const interactiveToolsStore = useInteractiveToolsStore();

        // Set up the network error for DELETE requests
        server.use(
            http.untyped.delete(/\/api\/entry_points\/.*/, () => {
                return HttpResponse.error();
            }),
        );

        // Try to stop the tool
        await wrapper.get(`#stop-${toolId}`).trigger("click");
        await flushPromises();

        // The error should be in the interactiveToolsStore messages
        expect(interactiveToolsStore.messages.length).toBeGreaterThan(0);
        expect(interactiveToolsStore.messages[0]).toMatch(/Network Error|Failed to fetch/);

        // The error should be displayed in the UI
        expect(wrapper.get(".alert-danger").text()).toMatch(/Network Error|Failed to fetch/);
    });
});
