import { createTestingPinia } from "@pinia/testing";
import { mount } from "@vue/test-utils";
import { PiniaVuePlugin } from "pinia";
import { getLocalVue } from "tests/jest/helpers";
import VueRouter from "vue-router";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { updateContentFields } from "@/components/History/model/queries";

import ContentItem from "./ContentItem.vue";

jest.mock("components/History/model/queries");

const { server, http } = useServerMock();

const localVue = getLocalVue();
localVue.use(VueRouter);
localVue.use(PiniaVuePlugin);
const router = new VueRouter();

jest.mock("vue-router/composables", () => ({
    useRoute: jest.fn(() => ({})),
    useRouter: jest.fn(() => ({})),
}));

// mock queries
updateContentFields.mockImplementation(async () => {});

const item = {
    id: "item_id",
    some_data: "some_data",
    tags: ["tag1", "tag2", "tag3"],
    deleted: false,
    visible: true,
};

describe("ContentItem", () => {
    let wrapper;

    beforeEach(() => {
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response }) => {
                // We need to use untyped here because this endpoint is not
                // described in the OpenAPI spec due to its complexity for now.
                return response.untyped(HttpResponse.json(item));
            })
        );

        wrapper = mount(ContentItem, {
            propsData: {
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
            localVue,
            stubs: {
                DatasetDetails: true,
                vueTagsInput: false,
            },
            provide: {
                store: {
                    dispatch: jest.fn,
                    getters: {},
                },
            },
            pinia: createTestingPinia(),
            router,
        });
    });

    it("check basics", async () => {
        expect(wrapper.attributes("data-hid")).toBe("1");
        expect(wrapper.find(".content-title").text()).toBe("name");
        const tags = wrapper.find(".stateless-tags").findAll(".tag");

        // verify tags
        expect(tags.length).toBe(3);

        for (let i = 0; i < 3; i++) {
            expect(tags.at(i).text()).toBe(`tag${i + 1}`);

            await tags.at(i).trigger("click");
            expect(wrapper.emitted()["tag-click"][i][0]).toBe(`tag${i + 1}`);
        }

        // close all tags
        for (let i = 0; i < 3; i++) {
            const tagRemover = wrapper.find(`.tag[data-option=tag${i + 1}] button`);

            await tagRemover.trigger("click");
            expect(wrapper.emitted()["tag-change"][i][1]).not.toContain(`tag${i + 1}`);
        }

        await wrapper.setProps({ isHistoryItem: false, item: { tags: [] } });
        expect(wrapper.find(".stateless-tags").exists()).toBe(false);

        // expansion button
        const $el = wrapper.find(".cursor-pointer");
        $el.trigger("click");
        expect(wrapper.emitted()["update:expand-dataset"]).toBeDefined();

        // select and unselect
        const noSelector = wrapper.find(".selector > svg");
        expect(noSelector.exists()).toBe(false);

        await wrapper.setProps({ selectable: true });
        expect(wrapper.classes()).toEqual(expect.arrayContaining(["alert-success"]));

        const selector = wrapper.find(".selector > svg");
        expect(selector.attributes("data-icon")).toBe("square");
        selector.trigger("click");

        await localVue.nextTick();
        expect(wrapper.emitted()["update:selected"][0][0]).toBe(true);

        await wrapper.setProps({ selected: true });
        selector.trigger("click");

        await localVue.nextTick();
        expect(wrapper.emitted()["update:selected"][1][0]).toBe(false);
        expect(wrapper.classes()).toEqual(expect.arrayContaining(["alert-info"]));
        expect(selector.attributes("data-icon")).toBe("check-square");
    });
});
