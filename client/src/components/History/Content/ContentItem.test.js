import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import ContentItem from "./ContentItem";
import { updateContentFields } from "components/History/model/queries";

jest.mock("components/History/model/queries");

const localVue = getLocalVue();

// mock queries
updateContentFields.mockImplementation(async () => {});

describe("ContentItem", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(ContentItem, {
            propsData: {
                expandDataset: true,
                item: {
                    id: "item_id",
                    some_data: "some_data",
                    tags: ["tag1", "tag2", "tag3"],
                    deleted: false,
                    visible: true,
                },
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
