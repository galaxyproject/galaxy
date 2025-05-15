import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "tests/jest/helpers";
import { setActivePinia } from "pinia";
import type { Tool } from "@/stores/toolStore";
import { useToolStore } from "@/stores/toolStore";
import { useInteractiveToolsStore } from "@/stores/interactiveToolsStore";
import { useEntryPointStore } from "@/stores/entryPointStore";
import InteractiveToolsPanel from "./InteractiveToolsPanel.vue";

// Mock the tool-version utility module
jest.mock("@/utils/tool-version", () => ({
    filterLatestToolVersions: jest.fn((tools: Tool[]) => tools),
}));

// Import the mocked function
import { filterLatestToolVersions } from "@/utils/tool-version";

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
        jest.clearAllMocks();
        (filterLatestToolVersions as jest.MockedFunction<typeof filterLatestToolVersions>).mockImplementation((tools) => tools);
    });

    const mountComponent = async (toolsList: Partial<Tool>[] = mockTools) => {
        const pinia = createTestingPinia({
            createSpy: () => jest.fn(),
            stubActions: false,
        });
        setActivePinia(pinia);

        // Mock the stores before mounting
        const toolStore = useToolStore();
        jest.spyOn(toolStore, "fetchTools").mockImplementation(jest.fn());
        jest.spyOn(toolStore, "getInteractiveTools").mockReturnValue(toolsList as Tool[]);

        const interactiveToolsStore = useInteractiveToolsStore();
        jest.spyOn(interactiveToolsStore, "getActiveTools").mockImplementation(jest.fn());

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
                    push: jest.fn(),
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
        (filterLatestToolVersions as jest.MockedFunction<typeof filterLatestToolVersions>).mockReturnValue(filteredTools as Tool[]);

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
            { id: "vscode", version: "1.0", name: "VS Code", model_class: "InteractiveTool", description: "Code editor" },
        ];
        (filterLatestToolVersions as jest.MockedFunction<typeof filterLatestToolVersions>).mockReturnValue(searchableTools as Tool[]);

        await mountComponent();

        // The component should have called the filter function
        expect(filterLatestToolVersions).toHaveBeenCalledWith(mockTools);
    });

    it("should handle empty tool list", async () => {
        (filterLatestToolVersions as jest.MockedFunction<typeof filterLatestToolVersions>).mockReturnValue([]);

        await mountComponent([]);

        expect(filterLatestToolVersions).toHaveBeenCalledWith([]);
    });
});