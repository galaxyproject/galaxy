import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import toolsList from "@/components/ToolsView/testData/toolsList.json";
import toolsListInPanel from "@/components/ToolsView/testData/toolsListInPanel.json";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { useToolStore } from "@/stores/toolStore";

import viewsList from "./testData/viewsList.json";

import ToolPanel from "./ToolPanel.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();
enableAutoUnmount(afterEach);

const DEFAULT_VIEW_ID = "default";
const NON_DEFAULT_VIEW_ID = "ontology:edam_operations";
const PANEL_VIEW_ERR_MSG = "Error loading panel view";
const DISCOVER_TOOLS = '[data-description="toolbox discover tools"]';

const firstTool = toolsList[0]!;
const toolsListWithExtraVersion = [...toolsList, { ...firstTool, id: `${firstTool.id}/0.9`, version: "0.9" }];

vi.mock("@/composables/config");
vi.mock("@/composables/userLocalStorage", () => ({ useUserLocalStorage: vi.fn() }));

interface PanelOptions {
    failedViews?: string[];
    panelResponses?: Record<string, unknown>;
    defaultPanelView?: string;
    captureToolsRequest?: (url: URL) => void;
    capturePanelRequest?: (panelView: string) => void;
}

function storePanelView(viewId: string) {
    vi.mocked(useUserLocalStorage).mockImplementation((key: string, initialValue: unknown) =>
        ref(key === "tool-store-view" ? viewId : initialValue),
    );
}

async function createWrapper({
    failedViews = [],
    panelResponses = {},
    defaultPanelView = DEFAULT_VIEW_ID,
    captureToolsRequest,
    capturePanelRequest,
}: PanelOptions = {}) {
    server.use(
        http.untyped.get("/api/tools", ({ request }) => {
            const url = new URL(request.url);
            captureToolsRequest?.(url);
            return HttpResponse.json(
                url.searchParams.get("in_panel")?.toLowerCase() === "false" ? toolsListWithExtraVersion : [],
            );
        }),
        http.untyped.get("/api/tool_panels", () =>
            HttpResponse.json({ default_panel_view: defaultPanelView, views: viewsList }),
        ),
        http.get("/api/users/{user_id}", ({ response }) => response(200).json(getFakeRegisteredUser())),
        ...(failedViews.length ? [...new Set([...failedViews, DEFAULT_VIEW_ID])] : Object.keys(viewsList)).map(
            (panelView) =>
                http.untyped.get(`/api/tool_panels/${panelView}`, () => {
                    capturePanelRequest?.(panelView);
                    if (failedViews.includes(panelView)) {
                        return HttpResponse.json({ err_msg: PANEL_VIEW_ERR_MSG }, { status: 400 });
                    }
                    return HttpResponse.json(panelResponses[panelView] ?? toolsListInPanel);
                }),
        ),
    );

    // The real menu, panel header, and toolbox are needed for their view-switching contract.
    const wrapper = mount(ToolPanel, {
        props: { workflow: false, useSearchWorker: false },
        global: { ...localVue, plugins: [...(localVue.plugins ?? []), createPinia()] },
    });
    await flushPromises();
    return wrapper;
}

describe("ToolPanel", () => {
    beforeEach(() => storePanelView(DEFAULT_VIEW_ID));

    it("opens the panel view menu with every available view", async () => {
        const wrapper = await createWrapper();
        expect(wrapper.find(".panel-view-selector").exists()).toBe(true);
        expect(wrapper.find("#toolbox-heading").text()).toBe("Tools");

        await wrapper.find("#toolbox-heading").trigger("click");
        await flushPromises();

        const dropdown = wrapper.find(".dropdown-menu");
        expect(dropdown.exists()).toBe(true);
        expect(dropdown.findAll(".dropdown-item")).toHaveLength(Object.keys(viewsList).length);
    });

    it.each(Object.values(viewsList))(
        "selects the $id view and reflects its name and icon in the header",
        async (view) => {
            const wrapper = await createWrapper();
            await wrapper.find("#toolbox-heading").trigger("click");
            await flushPromises();
            const item = wrapper.find(`.dropdown-menu [data-panel-id='${view.id}']`);

            if (view.id !== DEFAULT_VIEW_ID) {
                expect(item.attributes("title") || null).toBe(view.description);
                await item.trigger("click");
                await flushPromises();
            }

            expect(item.find("[data-description='panel view item icon']").exists()).toBe(true);
            expect(wrapper.find("[data-description='panel view header icon']").exists()).toBe(
                view.id !== DEFAULT_VIEW_ID && view.id !== "my_panel",
            );
            expect(wrapper.find("#toolbox-heading").text()).toBe(view.id === DEFAULT_VIEW_ID ? "Tools" : view.name);
        },
    );

    it("initializes the saved non-default panel view", async () => {
        storePanelView(NON_DEFAULT_VIEW_ID);
        const wrapper = await createWrapper();

        expect(wrapper.find(".alert").exists()).toBe(false);
        expect(wrapper.find("#toolbox-heading").text()).toBe(viewsList[NON_DEFAULT_VIEW_ID].name);
        expect(useToolStore().currentPanelView).toBe(NON_DEFAULT_VIEW_ID);
    });

    it("falls back to the default toolbox when the saved view fails to load", async () => {
        storePanelView(NON_DEFAULT_VIEW_ID);
        const wrapper = await createWrapper({ failedViews: [NON_DEFAULT_VIEW_ID] });

        expect(wrapper.find("#toolbox-heading").text()).not.toBe(viewsList[NON_DEFAULT_VIEW_ID].name);
        expect(wrapper.find("#toolbox-heading").text()).toBe("Tools");
        expect(useToolStore().currentPanelView).toBe(DEFAULT_VIEW_ID);
        expect(wrapper.find('[data-description="panel toolbox"]').exists()).toBe(true);
    });

    it("shows the loading error when both the saved and default views fail", async () => {
        storePanelView(NON_DEFAULT_VIEW_ID);
        const wrapper = await createWrapper({ failedViews: [NON_DEFAULT_VIEW_ID, DEFAULT_VIEW_ID] });

        expect(wrapper.find('[data-description="panel toolbox"]').exists()).toBe(false);
        expect(wrapper.find('[data-description="tool panel error message"]').text()).toBe(PANEL_VIEW_ERR_MSG);
    });

    it("hides the discover tools button when workflow mode is enabled", async () => {
        const wrapper = await createWrapper();
        expect(wrapper.find(DISCOVER_TOOLS).exists()).toBe(true);

        await wrapper.setProps({ workflow: true });

        expect(wrapper.find(DISCOVER_TOOLS).exists()).toBe(false);
    });

    it("counts the five fixture tools on the discover tools button", async () => {
        const wrapper = await createWrapper();
        expect(wrapper.find(DISCOVER_TOOLS).text()).toBe("Discover 5 Tools");
    });

    it("uses the default panel count while My Tools contains only a section label", async () => {
        storePanelView("my_panel");
        const wrapper = await createWrapper({
            panelResponses: {
                my_panel: {
                    recent_tools_label: {
                        model_class: "ToolSectionLabel",
                        id: "recent_tools_label",
                        text: "Recent tools",
                    },
                },
            },
        });

        expect(wrapper.find(DISCOVER_TOOLS).text()).toBe("Discover 5 Tools");
    });

    it("counts the loaded default panel rather than tool versions when My Tools is the backend default", async () => {
        storePanelView("");
        const wrapper = await createWrapper({
            defaultPanelView: "my_panel",
            panelResponses: {
                my_panel: { favorites: { model_class: "ToolSection", id: "favorites", name: "Favorites", tools: [] } },
            },
        });

        expect(wrapper.find(DISCOVER_TOOLS).text()).toBe("Discover 5 Tools");
        expect(wrapper.find(DISCOVER_TOOLS).text()).not.toBe(`Discover ${toolsListWithExtraVersion.length} Tools`);
    });

    it("ignores the single My Tools favorite for the header count when My Tools is the backend default", async () => {
        storePanelView("");
        const wrapper = await createWrapper({
            defaultPanelView: "my_panel",
            panelResponses: {
                my_panel: {
                    favorites: {
                        model_class: "ToolSection",
                        id: "favorites",
                        name: "Favorites",
                        tools: [firstTool.id],
                    },
                },
            },
        });

        expect(wrapper.find(DISCOVER_TOOLS).text()).toBe("Discover 5 Tools");
        expect(wrapper.find(DISCOVER_TOOLS).text()).not.toBe("Discover 1 Tools");
    });

    it("loads both the default panel sections and My Tools when My Tools is the backend default", async () => {
        storePanelView("");
        const requestedPanels: string[] = [];
        await createWrapper({
            defaultPanelView: "my_panel",
            panelResponses: {
                my_panel: { favorites: { model_class: "ToolSection", id: "favorites", name: "Favorites", tools: [] } },
            },
            capturePanelRequest: (panelView) => requestedPanels.push(panelView),
        });

        expect(requestedPanels).toContain(DEFAULT_VIEW_ID);
        expect(requestedPanels).toContain("my_panel");
    });

    it("requests tools outside the panel without requesting My Tools tags during default startup", async () => {
        const toolsRequested = vi.fn();
        const toolTagsRequested = vi.fn();
        server.use(
            http.untyped.get("/api/tags/tool_tags", () => {
                toolTagsRequested();
                return HttpResponse.json({});
            }),
        );
        await createWrapper({ captureToolsRequest: toolsRequested });

        expect(toolsRequested).toHaveBeenCalled();
        expect(toolsRequested.mock.calls[0]![0].searchParams.get("in_panel")).toBe("false");
        expect(toolTagsRequested).not.toHaveBeenCalled();
    });
});
