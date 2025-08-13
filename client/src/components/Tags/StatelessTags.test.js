import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import StatelessTags from "./StatelessTags";

describe("Tags/StatelessTags.vue", () => {

    const testTags = ["abc", "def", "ghi"];
    let wrapper;
    let emitted;

    beforeEach(async () => {
        const globalConfig = getLocalVue();
        wrapper = mount(StatelessTags, {
            props: {
                value: testTags,
            },
            global: globalConfig.global,
        });
        emitted = wrapper.emitted();
    });

    it("should render a div for each tag", () => {
        const tags = wrapper.findAll(".ti-tag-center");
        expect(tags.length).toBe(testTags.length);
        for (let i = 0; i < testTags.length; i++) {
            expect(tags[i].element.tagName).toBe("DIV");
            expect(tags[i].text()).toBe(testTags[i]);
        }
    });

    it("should emit a click event when the tag is clicked", () => {
        const tags = wrapper.findAll(".ti-tag-center > div");
        tags[0].trigger("click");
        expect(emitted["tag-click"]).toBeTruthy();
        expect(emitted["tag-click"].length).toBe(1);
    });

    it("should emit a tag model payload when tag is clicked", () => {
        const tags = wrapper.findAll(".ti-tag-center > div");
        tags[0].trigger("click");
        const firstEvent = emitted["tag-click"][0];
        const firstArg = firstEvent[0];
        expect(firstArg.text).toBe(testTags[0]);
    });

    it("should change internal model representation when new tag list assigned", async () => {
        expect(wrapper.vm.tagModels.length).toBe(3);
        const newTags = ["floob", "clown", "hoohah", "doodoo"];
        await wrapper.setProps({ value: newTags });
        expect(wrapper.vm.tagModels.length).toBe(newTags.length);
    });
});
