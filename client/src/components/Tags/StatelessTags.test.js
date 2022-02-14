import { mount, createLocalVue } from "@vue/test-utils";
import StatelessTags from "./StatelessTags";
import _l from "utils/localization";
import flushPromises from "flush-promises";

describe("Tags/StatelessTags.vue", () => {
    const localVue = createLocalVue();
    localVue.filter("localize", (value) => _l(value));

    const testTags = ["abc", "def", "ghi"];
    let wrapper;
    let emitted;

    beforeEach(async () => {
        wrapper = mount(StatelessTags, { localVue });
        wrapper.setProps({
            value: testTags,
        });
        emitted = wrapper.emitted();
        await wrapper.vm.$nextTick();
    });

    it("should render a div for each tag", () => {
        const tags = wrapper.findAll(".ti-tag-center");
        expect(tags.length).toBe(testTags.length);
        for (let i = 0; i < testTags.length; i++) {
            expect(tags.at(i).element.tagName).toBe("DIV");
            expect(tags.at(i).text()).toBe(testTags[i]);
        }
    });

    it("should emit a click event when the tag is clicked", () => {
        const tags = wrapper.findAll(".ti-tag-center > div");
        tags.at(0).trigger("click");
        expect(emitted["tag-click"]).toBeTruthy();
        expect(emitted["tag-click"].length).toBe(1);
    });

    it("should emit a tag model payload when tag is clicked", () => {
        const tags = wrapper.findAll(".ti-tag-center > div");
        tags.at(0).trigger("click");
        const firstEvent = emitted["tag-click"][0];
        const firstArg = firstEvent[0];
        expect(firstArg.text).toBe(testTags[0]);
    });

    it("should change internal model representation when new tag list assigned", async () => {
        expect(wrapper.vm.tagModels.length).toBe(3);
        const newTags = ["floob", "clown", "hoohah", "doodoo"];
        wrapper.setProps({ value: newTags });
        await flushPromises();
        expect(wrapper.vm.tagModels.length).toBe(newTags.length);
    });
});
