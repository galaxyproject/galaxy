import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import toolsList from "@/components/ToolsView/testData/toolsList.json";
import toolsListInPanel from "@/components/ToolsView/testData/toolsListInPanel.json";
import { useUserLocalStorage } from "@/composables/userLocalStorage";
import { useToolStore } from "@/stores/toolStore";

import viewsListJson from "./testData/viewsList.json";
import { types_to_icons } from "./utilities";

import ToolPanel from "./ToolPanel.vue";

interface ToolPanelView {
    id: string;
    model_class: string;
    name: string;
    description: string | null;
    view_type: string;
    searchable: boolean;
}

const localVue = getLocalVue();
const router = injectTestRouter(localVue);
const { server, http } = useServerMock();

const TEST_PANELS_URI = "/api/tool_panels";
const DEFAULT_VIEW_ID = "default";
const PANEL_VIEW_ERR_MSG = "Error loading panel view";

vi.mock("@/composables/config");

vi.mock("@/composables/userLocalStorage", () => ({
    useUserLocalStorage: vi.fn((_key: string, initialValue: unknown) =>
        ref(_key === "tool-store-view" ? DEFAULT_VIEW_ID : initialValue),
    ),
}));

describe("ToolPanel", () => {
    const viewsList = viewsListJson as Record<string, ToolPanelView>;

    /** Mocks and stores a non-default panel view as the current panel view */
    function storeNonDefaultView() {
        // find a view in object viewsList that is not DEFAULT_VIEW_ID
        const viewKey = Object.keys(viewsList).find((id) => id !== DEFAULT_VIEW_ID);
        if (!viewKey) {
            throw new Error("No non-default view found in viewsList");
        }
        const view = viewsList[viewKey];
        if (!view) {
            throw new Error(`View with key ${viewKey} not found in viewsList`);
        }
        // ref and useUserLocalStorage are already imported at the top
        vi.mocked(useUserLocalStorage).mockImplementation((_key: string, initialValue: unknown) =>
            ref(_key === "tool-store-view" ? viewKey : initialValue),
        );
        return { viewKey, view };
    }

    /**
     * Sets up wrapper for ToolPanel component
     * @param {String} errorView If provided, we mock an error for this view
     * @param {Boolean} failDefault If true and error view is provided, we
     *                              mock an error for the default view as well
     * @returns wrapper
     */
    async function createWrapper(errorView: string = "", failDefault: boolean = false) {
        server.use(
            http.untyped.get("/api/tools", ({ request }) => {
                const url = new URL(request.url);
                if (url.searchParams.get("in_panel") === "False") {
                    return HttpResponse.json(toolsList);
                }
                return HttpResponse.json([]);
            }),
            http.untyped.get(TEST_PANELS_URI, () => {
                return HttpResponse.json({ default_panel_view: DEFAULT_VIEW_ID, views: viewsList });
            }),
            http.get("/api/users/{user_id}", ({ response }) => {
                return response(200).json(getFakeRegisteredUser());
            }),
        );

        if (errorView) {
            server.use(
                http.untyped.get(`/api/tool_panels/${errorView}`, () => {
                    return HttpResponse.json({ err_msg: PANEL_VIEW_ERR_MSG }, { status: 400 });
                }),
            );
            if (errorView !== DEFAULT_VIEW_ID && !failDefault) {
                server.use(
                    http.untyped.get(`/api/tool_panels/${DEFAULT_VIEW_ID}`, () => {
                        return HttpResponse.json(toolsListInPanel);
                    }),
                );
            } else if (failDefault) {
                server.use(
                    http.untyped.get(`/api/tool_panels/${DEFAULT_VIEW_ID}`, () => {
                        return HttpResponse.json({ err_msg: PANEL_VIEW_ERR_MSG }, { status: 400 });
                    }),
                );
            }
        } else {
            // mock response for all panel views
            server.use(
                http.untyped.get(/\/api\/tool_panels\/.*/, () => {
                    return HttpResponse.json(toolsListInPanel);
                }),
            );
        }

        // setting this because for the default view, we just show "Tools" as the name
        // even though the backend returns "Full Tool Panel"
        viewsList[DEFAULT_VIEW_ID]!.name = "Tools";

        const pinia = createPinia();
        const wrapper = mount(ToolPanel as object, {
            propsData: {
                workflow: false,
                editorWorkflows: null,
                useSearchWorker: false,
            },
            localVue,
            router,
            pinia,
        });

        await flushPromises();

        return wrapper;
    }

    it("test navigation of tool panel views menu", async () => {
        const wrapper = await createWrapper();
        // there is a panel view selector initially collapsed
        expect(wrapper.find(".panel-view-selector").exists()).toBeTruthy();

        // Test: starts up with a default panel view, click to open menu
        expect(wrapper.find("#toolbox-heading").text()).toBe(viewsList[DEFAULT_VIEW_ID]!.name);
        await wrapper.find("#toolbox-heading").trigger("click");
        await flushPromises();

        const dropdownMenu = wrapper.find(".dropdown-menu");
        expect(dropdownMenu.exists()).toBeTruthy();

        // Test: check if the dropdown menu has all the panel views
        const dropdownItems = dropdownMenu.findAll(".dropdown-item");
        expect(dropdownItems.length).toEqual(Object.keys(viewsList).length);

        // Test: click on each panel view, and check if the panel view is changed
        for (const [key, value] of Object.entries(viewsList)) {
            // find dropdown item
            const currItem = dropdownMenu.find(`[data-panel-id='${key}']`);
            if (key !== DEFAULT_VIEW_ID) {
                // Test: check if the panel view has appropriate description
                const description = currItem.attributes().title || null;
                expect(description).toBe(value.description);

                // set current panel view
                await currItem.trigger("click");
                await flushPromises();

                // Test: check if the current panel view is selected now
                expect(currItem.find("[data-description='panel view item icon']").attributes("data-icon")).toEqual(
                    "check",
                );

                // Test: check if the panel header now has an icon and a changed name
                const currentViewType = value.view_type as keyof typeof types_to_icons;
                const panelViewIcon = wrapper.find("[data-description='panel view header icon']");
                if (key === "my_panel") {
                    expect(panelViewIcon.exists()).toBe(false);
                } else {
                    expect(panelViewIcon.attributes("data-icon")).toEqual(types_to_icons[currentViewType].iconName);
                }
                expect(wrapper.find("#toolbox-heading").text()).toBe(value!.name);
            } else {
                // Test: check if the default panel view is already selected, and no icon
                expect(currItem.find("[data-description='panel view item icon']").attributes("data-icon")).toEqual(
                    "check",
                );
                expect(wrapper.find("[data-description='panel view header icon']").exists()).toBe(false);
            }
        }
    });

    it("initializes non default current panel view correctly", async () => {
        const { viewKey, view } = storeNonDefaultView();
        const wrapper = await createWrapper();
        expect(wrapper.find(".alert").exists()).toBeFalsy();
        expect(wrapper.find("#toolbox-heading").text()).toBe(view!.name);
        const toolStore = useToolStore();
        expect(toolStore.currentPanelView).toBe(viewKey);
    });

    it("changes panel to default if current panel view throws error", async () => {
        const { viewKey, view } = storeNonDefaultView();
        const wrapper = await createWrapper(viewKey);
        expect(wrapper.find("#toolbox-heading").text()).not.toBe(view!.name);
        expect(wrapper.find("#toolbox-heading").text()).toBe(viewsList[DEFAULT_VIEW_ID]!.name);
        const toolStore = useToolStore();
        expect(toolStore.currentPanelView).toBe(DEFAULT_VIEW_ID);
        expect(wrapper.find('[data-description="panel toolbox"]').exists()).toBe(true);
    });

    it("simply shows error if even default panel view throws error", async () => {
        const { viewKey } = storeNonDefaultView();
        const wrapper = await createWrapper(viewKey, true);
        expect(wrapper.find('[data-description="panel toolbox"]').exists()).toBeFalsy();
        expect(wrapper.find('[data-description="tool panel error message"]').text()).toBe(PANEL_VIEW_ERR_MSG);
    });

    it("shows go to all button when not in workflow mode and hides it in workflow mode", async () => {
        const wrapper = await createWrapper();

        // Test: go to all button should appear when workflow is false (default)
        expect(wrapper.find('[data-description="toolbox discover tools"]').exists()).toBe(true);

        // Test: change workflow prop to true and button should disappear
        await wrapper.setProps({ workflow: true });

        expect(wrapper.find('[data-description="Discover Tools button"]').exists()).toBe(false);
    });

    it("shows the tools count on the discover tools button", async () => {
        const wrapper = await createWrapper();
        const count = toolsList.length;
        const formatted = count < 1000 ? `${count}` : `${Math.floor(count / 1000)}k+`;
        const discoverButton = wrapper.find('[data-description="toolbox discover tools"]');
        expect(discoverButton.text()).toBe(`Discover ${formatted} Tools`);
    });
});
