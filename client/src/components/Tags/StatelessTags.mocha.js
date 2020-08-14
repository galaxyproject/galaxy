import { mount, createLocalVue } from "@vue/test-utils";
import StatelessTags from "./StatelessTags";
import _l from "utils/localization";
import Vue from "vue";

describe("Tags/StatelessTags.vue", () => {
    const localVue = createLocalVue();
    localVue.filter("localize", (value) => _l(value));

    let testTags = ["abc", "def", "ghi"];
    let wrapper, emitted;

    beforeEach(async () => {
        wrapper = mount(StatelessTags, { localVue });
        wrapper.setProps({
            value: testTags,
        });
        emitted = wrapper.emitted();
        await Vue.nextTick();
    });

    it("should render a div for each tag", () => {
        let tags = wrapper.findAll(".ti-tag-center");
        assert(tags.length == testTags.length, "Wrong number of tags");
        for (let i = 0; i < testTags.length; i++) {
            assert(tags.at(i).is("div"), "button not a div");
            assert(tags.at(i).text() == testTags[i], "rendered tag label doesn't match test data");
        }
    });

    it("should emit a click event when the tag is clicked", () => {
        let tags = wrapper.findAll(".ti-tag-center > div");
        tags.at(0).trigger("click");
        assert(emitted["tag-click"], "click event not detected");
        assert(emitted["tag-click"].length == 1, "wrong event count");
    });

    it("should emit a tag model payload when tag is clicked", () => {
        let tags = wrapper.findAll(".ti-tag-center > div");
        tags.at(0).trigger("click");
        let firstEvent = emitted["tag-click"][0];
        let firstArg = firstEvent[0];
        assert((firstArg.text = testTags[0]), "returned tag model doesn't match test data");
    });

    it("should change internal model representation when new tag list assigned", async () => {
        assert(wrapper.vm.tagModels.length == 3);
        let newTags = ["floob", "clown", "hoohah", "doodoo"];
        wrapper.setProps({ value: newTags });
        assert(wrapper.vm.tagModels.length == newTags.length);
    });
});
