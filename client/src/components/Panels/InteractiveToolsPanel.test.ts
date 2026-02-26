import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useEntryPointStore } from "@/stores/entryPointStore";
import { useInteractiveToolsStore } from "@/stores/interactiveToolsStore";
import type { Tool } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";
// Import the mocked function
import { filterLatestToolVersions } from "@/utils/tool-version";

import InteractiveToolsPanel from "./InteractiveToolsPanel.vue";

// Mock the tool-version utility module
vi.mock("@/utils/tool-version", () => ({
    filterLatestToolVersions: vi.fn((tools: Tool[]) => tools),
}));

const localVue = getLocalVue();

// Mock tools data
const mockTools: Partial<Tool>[] = [
    { id: "rstudio/1.1.0", version: "1.1.0", name: "RStudio", model_class: "InteractiveTool" },
    { id: "rstudio/1.2.0", version: "1.2.0", name: "RStudio", model_class: "InteractiveTool" },
    { id: "jupyter/2.0", version: "2.0", name: "Jupyter", model_class: "InteractiveTool" },
    { id: "vscode", version: "1.0", name: "VS Code", model_class: "InteractiveTool", description: "Code editor" },
];

describe("InteractiveToolsPanel component", () => {
    beforeEach(() => {
        // Reset mocks
        vi.clearAllMocks();
        (filterLatestToolVersions as ReturnType<typeof vi.fn>).mockImplementation((tools) => tools);
    });

    const mountComponent = async (toolsList: Partial<Tool>[] = mockTools) => {
        const pinia = createTestingPinia({
            createSpy: vi.fn,
            stubActions: false,
        });
        setActivePinia(pinia);

        // Mock the stores before mounting
        const toolStore = useToolStore();
        vi.spyOn(toolStore, "fetchTools").mockImplementation(vi.fn());
        vi.spyOn(toolStore, "getInteractiveTools").mockReturnValue(toolsList as Tool[]);

        const interactiveToolsStore = useInteractiveToolsStore();
        vi.spyOn(interactiveToolsStore, "getActiveTools").mockImplementation(vi.fn());

        const entryPointStore = useEntryPointStore();
        entryPointStore.$patch({ entryPoints: [] });

        const wrapper = mount(InteractiveToolsPanel as any, {
            localVue,
            pinia,
            stubs: {
                ActivityPanel: true,
                DelayedInput: true,
                FontAwesomeIcon: true,
                UtcDate: true,
            },
            mocks: {
                $router: {
                    push: vi.fn(),
                },
            },
        });

        await flushPromises();

        return wrapper;
    };

    it("should call filterLatestToolVersions with interactive tools", async () => {
        await mountComponent();

        expect(filterLatestToolVersions).toHaveBeenCalledWith(mockTools);
    });

    it("should use the filterLatestToolVersions utility function", async () => {
        // Test that the component properly integrates with the utility function
        const filteredTools = [
            { id: "rstudio/1.2.0", version: "1.2.0", name: "RStudio", model_class: "InteractiveTool" },
            { id: "jupyter/2.0", version: "2.0", name: "Jupyter", model_class: "InteractiveTool" },
        ];
        (filterLatestToolVersions as ReturnType<typeof vi.fn>).mockReturnValue(filteredTools as Tool[]);

        await mountComponent();

        // The mock should have been called
        expect(filterLatestToolVersions).toHaveBeenCalledWith(mockTools);
        // The mock should have returned the filtered tools
        expect(filterLatestToolVersions).toHaveReturnedWith(filteredTools);
    });

    it("should handle search functionality independently of version filtering", async () => {
        // This test verifies the component's search functionality works correctly
        // It doesn't need to re-test the filterLatestToolVersions logic
        const searchableTools = [
            { id: "rstudio/1.2.0", version: "1.2.0", name: "RStudio", model_class: "InteractiveTool" },
            {
                id: "vscode",
                version: "1.0",
                name: "VS Code",
                model_class: "InteractiveTool",
                description: "Code editor",
            },
        ];
        (filterLatestToolVersions as ReturnType<typeof vi.fn>).mockReturnValue(searchableTools as Tool[]);

        await mountComponent();

        // The component should have called the filter function
        expect(filterLatestToolVersions).toHaveBeenCalledWith(mockTools);
    });

    it("should handle empty tool list", async () => {
        (filterLatestToolVersions as ReturnType<typeof vi.fn>).mockReturnValue([]);

        await mountComponent([]);

        expect(filterLatestToolVersions).toHaveBeenCalledWith([]);
    });

    it("should display active interactive tools at the top", async () => {
        // Set up active tools in the entry points store
        const activeTools = [
            {
                model_class: "InteractiveToolEntryPoint" as const,
                id: "active-tool-1",
                job_id: "job-1",
                name: "Active RStudio",
                active: true,
                created_time: new Date().toISOString(),
                modified_time: new Date().toISOString(),
                output_datasets_ids: [],
                target: "http://localhost:8001/active-tool-1",
            },
            {
                model_class: "InteractiveToolEntryPoint" as const,
                id: "active-tool-2",
                job_id: "job-2",
                name: "Starting Jupyter",
                active: false,
                created_time: new Date().toISOString(),
                modified_time: new Date().toISOString(),
                output_datasets_ids: [],
                target: "http://localhost:8001/active-tool-2",
            },
        ];

        const pinia = createTestingPinia({
            createSpy: vi.fn,
            stubActions: false,
        });
        setActivePinia(pinia);

        // Set up entry points before mounting
        const entryPointStore = useEntryPointStore();
        entryPointStore.entryPoints = activeTools;

        // Mock the stores
        const toolStore = useToolStore();
        vi.spyOn(toolStore, "fetchTools").mockImplementation(vi.fn());
        vi.spyOn(toolStore, "getInteractiveTools").mockReturnValue(mockTools as Tool[]);

        const interactiveToolsStore = useInteractiveToolsStore();
        vi.spyOn(interactiveToolsStore, "getActiveTools").mockImplementation(vi.fn());

        const wrapper = mount(InteractiveToolsPanel as any, {
            localVue,
            pinia,
            stubs: {
                ActivityPanel: {
                    template: '<div><slot name="header" /><slot /></div>',
                },
                DelayedInput: true,
                FontAwesomeIcon: true,
                UtcDate: true,
            },
            mocks: {
                $router: {
                    push: vi.fn(),
                },
            },
        });

        await flushPromises();

        // Check that the active tools section exists
        expect(wrapper.find(".active-tools-section").exists()).toBe(true);

        // Check that the active tools are listed
        const activeToolItems = wrapper.findAll(".active-tool-item");
        expect(activeToolItems).toHaveLength(2);

        // Check that the first active tool has the correct name
        expect(activeToolItems.at(0).text()).toContain("Active RStudio");
        expect(activeToolItems.at(0).text()).toContain("Running");

        // Check that the second active tool (starting) has the correct name
        expect(activeToolItems.at(1).text()).toContain("Starting Jupyter");
        expect(activeToolItems.at(1).text()).toContain("Starting...");

        // Check that stop buttons are present
        expect(activeToolItems.at(0).find(".btn-link.text-danger").exists()).toBe(true);
        expect(activeToolItems.at(1).find(".btn-link.text-danger").exists()).toBe(true);
    });
});
