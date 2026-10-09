import { createTestingPinia } from "@pinia/testing";
import { emittedArg, getLocalVue, suppressLucideVue2Deprecation, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { updateContentFields } from "@/components/History/model/queries";

import ContentItem from "./ContentItem.vue";

vi.mock("@/components/History/model/queries");

const { server, http } = useServerMock();

enableAutoUnmount(afterEach);
afterEach(() => vi.restoreAllMocks());

vi.mock("vue-router", async (importOriginal) => ({
    ...(await importOriginal()),
    useRoute: vi.fn(() => ({})),
    useRouter: vi.fn(() => ({})),
}));

function makeItem() {
    return {
        id: "item_id",
        some_data: "some_data",
        tags: ["tag1", "tag2", "tag3"],
        deleted: false,
        visible: true,
    };
}

beforeEach(() => {
    suppressLucideVue2Deprecation();
    vi.mocked(updateContentFields).mockReset().mockResolvedValue(undefined);
});

function mountContentItem() {
    const item = makeItem();
    const localVue = getLocalVue();
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    const router = createRouter({ history: createMemoryHistory(), routes: [] });
    server.use(
        http.get("/api/object_stores", ({ response }) => {
            return response(200).json([]);
        }),

        http.get("/api/datasets/{dataset_id}", ({ response }) => {
            // We need to use untyped here because this endpoint is not
            // described in the OpenAPI spec due to its complexity for now.
            return response.untyped(HttpResponse.json(item));
        }),
    );

    return mount(ContentItem, {
        props: {
            expandDataset: true,
            item,
            id: 1,
            isDataset: true,
            isHistoryItem: true,
            name: "name",
            selected: false,
            selectable: false,
            filterable: true,
        },
        global: withPlugins(localVue, pinia, router),
        stubs: {
            DatasetDetails: true,
            vueTagsInput: false,
        },
        provide: {
            store: {
                dispatch: vi.fn,
                getters: {},
            },
        },
    });
}

describe("ContentItem", () => {
    it("renders the history item number, name, and all tags", () => {
        const wrapper = mountContentItem();
        expect(wrapper.attributes("data-hid")).toBe("1");
        expect(wrapper.get(".content-title").text()).toBe("name");
        expect(wrapper.findAll(".stateless-tags .tag").map((tag) => tag.text())).toEqual(["tag1", "tag2", "tag3"]);
    });

    it("emits each tag when clicked", async () => {
        const wrapper = mountContentItem();
        const tags = wrapper.findAll(".stateless-tags .tag");
        for (const [index, tag] of tags.entries()) {
            await tag.trigger("click");
            expect(emittedArg(wrapper, "tag-click", index)).toBe(`tag${index + 1}`);
        }
    });

    it("emits tags with each removed tag excluded, then hides empty non-history tags", async () => {
        const wrapper = mountContentItem();
        for (const [index, tag] of ["tag1", "tag2", "tag3"].entries()) {
            await wrapper.get(`.tag[data-option=${tag}] button`).trigger("click");
            expect(wrapper.emitted("tag-change")[index][1]).not.toContain(tag);
        }
        await wrapper.setProps({ isHistoryItem: false, item: { tags: [] } });
        expect(wrapper.find(".stateless-tags").exists()).toBe(false);
    });

    it("emits collapse when the expanded dataset header is clicked", async () => {
        const wrapper = mountContentItem();
        await wrapper.setProps({ isHistoryItem: false, item: { tags: [] } });
        await wrapper.get(".cursor-pointer").trigger("click");
        expect(emittedArg(wrapper, "update:expand-dataset")).toBe(false);
    });

    it("shows selection on demand and emits select then unselect", async () => {
        const wrapper = mountContentItem();
        await wrapper.setProps({ isHistoryItem: false, item: { tags: [] } });
        expect(wrapper.find(".selector > svg").exists()).toBe(false);
        await wrapper.setProps({ selectable: true });
        expect(wrapper.classes()).toContain("alert-success");

        const selector = wrapper.get(".selector > svg");
        expect(selector.attributes("data-icon")).toBe("square");
        await selector.trigger("click");
        expect(emittedArg(wrapper, "update:selected")).toBe(true);

        await wrapper.setProps({ selected: true });
        const checkedSelector = wrapper.get(".selector > svg");
        expect(checkedSelector.attributes("data-icon")).toBe("check-square");
        await checkedSelector.trigger("click");
        expect(emittedArg(wrapper, "update:selected", 1)).toBe(false);
        expect(wrapper.classes()).toContain("alert-info");
    });
});
