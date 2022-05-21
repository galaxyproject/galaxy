import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import ContentItem from "./ContentItem";

const localVue = getLocalVue();

describe("ContentItem", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(ContentItem, {
            propsData: {
                expandDataset: false,
                item: {
                    id: "item_id",
                    some_data: "some_data",
                    tags: ["tag1", "tag2", "tag3"],
                    deleted: false,
                    visible: true,
                },
                id: 1,
                isDataset: true,
                isHistoryItem: false,
                name: "name",
                selected: false,
                selectable: false,
            },
            localVue,
        });
    });

    it("check basics", async () => {
        expect(wrapper.attributes("data-hid")).toBe("1");
        expect(wrapper.find(".content-title").text()).toBe("name");
        const tags = wrapper.find(".nametags").findAll(".badge");
        // verify tags
        expect(tags.length).toBe(3);
        for (let i = 0; i < 3; i++) {
            expect(tags.at(i).text()).toBe(`tag${i + 1}`);
        }
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
