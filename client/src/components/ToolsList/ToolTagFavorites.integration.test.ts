import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ToolBox from "@/components/Panels/ToolBox.vue";
import { createWhooshQuery } from "@/components/Panels/utilities";
import toolsListUntyped from "@/components/ToolsView/testData/toolsList.json";
import toolsListInPanelUntyped from "@/components/ToolsView/testData/toolsListInPanel.json";
import { setMockConfig } from "@/composables/__mocks__/config";
import { type Tool, type ToolSection, useToolStore } from "@/stores/toolStore";
import { useUserStore } from "@/stores/userStore";

import ToolsListCard from "./ToolsListCard.vue";
import ToolsList from "./ToolsList.vue";

vi.mock("@/composables/config");

const routerPushMock = vi.fn();

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: routerPushMock,
    }),
}));

vi.mock("@/components/Form/Elements/FormSelect.vue", () => ({
    default: {
        name: "FormSelect",
        props: ["id", "disabled", "multiple", "optional", "options", "value", "placeholder"],
        render(h: (tag: string, data?: Record<string, unknown>) => unknown) {
            return h("div", { attrs: { "data-description": "form-select-stub" } });
        },
    },
}));

const localVue = getLocalVue();
const router = injectTestRouter(localVue);
const toolsList = toolsListUntyped as unknown as Tool[];
const toolsListInPanel = toolsListInPanelUntyped as unknown as Record<string, Tool | ToolSection>;

setMockConfig({
    toolbox_auto_sort: true,
});

function toToolsById(list: Tool[]) {
    return list.reduce(
        (acc, tool) => {
            acc[tool.id] = tool;
            return acc;
        },
        {} as Record<string, Tool>,
    );
}

describe("Tool tag favorites integration", () => {
    beforeEach(() => {
        routerPushMock.mockClear();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it("filters by tag in Discover Tools and shows the favorited tag in My Tools", async () => {
        vi.useFakeTimers();

        const pinia = createPinia();
        setActivePinia(pinia);

        const toolStore = useToolStore();
        toolStore.toolsById = toToolsById(toolsList);
        toolStore.toolSections = { default: toolsListInPanel };
        toolStore.defaultPanelView = "default";
        toolStore.currentPanelView = "default";

        const fetchToolsMock = vi.spyOn(toolStore, "fetchTools").mockResolvedValue();
        vi.spyOn(toolStore, "fetchToolSections").mockResolvedValue();
        vi.spyOn(toolStore, "fetchHelpForId").mockResolvedValue();

        const userStore = useUserStore();
        userStore.currentUser = {
            id: "user-id",
            username: "test-user",
            email: "test@example.org",
            isAnonymous: false,
        } as any;
        userStore.currentPreferences = { favorites: { tools: [], tags: [] } };

        vi.spyOn(userStore, "addFavoriteTag").mockImplementation(async (tag: string) => {
            userStore.currentPreferences = {
                favorites: {
                    tools: userStore.currentPreferences?.favorites.tools ?? [],
                    tags: [...(userStore.currentPreferences?.favorites.tags ?? []), tag],
                },
            };
        });

        const toolsListWrapper = mount(ToolsList as object, {
            pinia,
            localVue,
            router,
        });

        await flushPromises();
        routerPushMock.mockClear();

        const input = toolsListWrapper.find("input.search-query");
        await input.setValue("tag:collection_ops");
        vi.advanceTimersByTime(400);
        await flushPromises();

        expect(routerPushMock).toHaveBeenLastCalledWith({
            path: "/tools/list",
            query: {
                tag: ["collection_ops"],
            },
        });
        expect(fetchToolsMock).toHaveBeenLastCalledWith(
            createWhooshQuery({
                tag: ["collection_ops"],
            }),
            { includeToolTags: true },
        );

        const tagCardWrapper = mount(ToolsListCard as object, {
            pinia,
            localVue,
            propsData: {
                id: "__ZIP_COLLECTION__",
                name: "Zip Collection",
                edamOperations: [],
                edamTopics: [],
                toolTags: ["collection_ops", "dataset_collections"],
                workflowCompatible: true,
                local: true,
                fetching: false,
            },
        });

        await tagCardWrapper.find(".inline-tag-button").trigger("click");
        await flushPromises();

        toolStore.currentPanelView = "my_panel";

        const toolboxWrapper = mount(ToolBox as object, {
            pinia,
            localVue,
            router,
            propsData: {
                favoritesDefault: true,
                useSearchWorker: false,
            },
        });

        await flushPromises();

        const tagSection = toolboxWrapper
            .findAll(".toolSectionTitle")
            .wrappers.find((item) => item.text().includes("collection_ops"));
        expect(tagSection).toBeTruthy();

        await tagSection?.find(".title-link").trigger("click");
        await flushPromises();

        expect(toolboxWrapper.find('[data-tool-id="__ZIP_COLLECTION__"]').exists()).toBe(true);
    });
});
