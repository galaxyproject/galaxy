import { composeStory } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { disposePinia, getActivePinia } from "pinia";
import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { nextTick } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useEntryPointStore } from "@/stores/entryPointStore";
import { useInteractiveToolsStore } from "@/stores/interactiveToolsStore";

import * as Stories from "./InteractiveTools.stories";
import { interactiveToolsHandlers } from "./test_fixtures";
import testInteractiveToolsResponse from "./testData/testInteractiveToolsResponse.json";

// Mock the rethrowSimple function to prevent test failures
vi.mock("@/utils/simple-error", async (importOriginal) => ({
    ...(await importOriginal()),
    rethrowSimple: vi.fn(),
    errorMessageAsString: vi.fn((error) => error.message),
}));

const { server, http } = useServerMock();
const mountStory = useStoryMount();

describe("InteractiveTools/InteractiveTools.vue", () => {
    async function mountTools() {
        // Set up the GET response for entry points - use a copy to avoid modifications between tests
        const testData = structuredClone(testInteractiveToolsResponse);
        const story = composeStory(
            { ...Stories.RunningTools, parameters: { msw: { handlers: interactiveToolsHandlers(testData) } } },
            Stories.default,
        );
        const wrapper = mountStory(story, {
            pinia: {
                initialState: {
                    entryPointStore: { entryPoints: testData },
                    interactiveToolsStore: { messages: [], activeTools: testData },
                },
                stubActions: false,
            },
        });
        const pinia = getActivePinia();
        onTestFinished(() => disposePinia(pinia));

        // Wait for any async operations to complete
        await flushPromises();
        return { wrapper, pinia };
    }

    afterEach(() => {
        vi.clearAllMocks();
    });

    it("renders table with interactive tools", async () => {
        const { wrapper } = await mountTools();
        expect(wrapper.find("#g-table-interactive-tool-table").exists()).toBeTruthy();
        // Each entry has 2 links: one to open inline (rendered as button) and one to open in new tab (rendered as anchor)
        expect(wrapper.findAll("td > button.g-link").length).toBe(2);
        expect(wrapper.findAll("td > a").length).toBe(2);
    });

    it("filters the table with the search GFormInput", async () => {
        const { wrapper } = await mountTools();
        const firstTool = nth(testInteractiveToolsResponse, 0);
        const search = wrapper.get("#interactivetool-search");
        expect(search.classes()).toContain("g-form-input");
        await search.setValue("no tool has this name");
        expect(wrapper.find(`#link-${firstTool.id}`).exists()).toBeFalsy();
    });

    it("displays interactive tool information correctly", async () => {
        const { wrapper } = await mountTools();
        const firstTool = nth(testInteractiveToolsResponse, 0);
        const toolName = wrapper.get(`#link-${firstTool.id}`);
        expect(toolName.text()).toContain(firstTool.name);

        // Check if the external link is present
        const externalLink = wrapper.find(`#external-link-${firstTool.id}`);
        expect(externalLink.exists()).toBeTruthy();
        expect(externalLink.attributes("href")).toBe(firstTool.target);
        expect(externalLink.attributes("target")).toBe("_blank");
    });

    it("removes the interactive tool when it is gone from store", async () => {
        const { wrapper, pinia } = await mountTools();
        const firstTool = nth(testInteractiveToolsResponse, 0);

        function checkIfExists(tag, id) {
            return wrapper.find(tag + id).exists();
        }

        expect(checkIfExists("#link-", firstTool.id)).toBeTruthy();

        // drop the tested tool from store
        const store = useEntryPointStore(pinia);
        store.entryPoints.splice(0, 1);
        await nextTick();

        expect(checkIfExists("#link-", firstTool.id)).toBeFalsy();
    });

    it("sends a delete request after the stop button is pressed", async () => {
        const { wrapper } = await mountTools();
        const deleteRequests = [];
        const firstTool = nth(testInteractiveToolsResponse, 0);
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
        expect(nth(deleteRequests, 0).url.includes(toolId)).toBeTruthy();
    });

    it("shows an error message if the tool deletion fails", async () => {
        const { wrapper, pinia } = await mountTools();
        const firstTool = nth(testInteractiveToolsResponse, 0);
        const toolId = firstTool.id;
        const interactiveToolsStore = useInteractiveToolsStore(pinia);

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
        expect(nth(interactiveToolsStore.messages, 0)).toMatch(/Network Error|Failed to fetch/);

        // The error should be displayed in the UI
        expect(wrapper.get(".alert-danger").text()).toMatch(/Network Error|Failed to fetch/);
    });
});
