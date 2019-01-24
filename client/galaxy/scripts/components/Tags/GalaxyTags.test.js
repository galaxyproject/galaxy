import { mount } from "@vue/test-utils";
import GalaxyTags from "./GalaxyTags";

describe("Tags/GalaxyTags.vue", () => {

    const testTags = ["abc", "def", "ghi"];

    let wrapper, emitted;

    beforeEach(function () {
        wrapper = mount(GalaxyTags);
        wrapper.setProps({
            value: testTags
        });
        emitted = wrapper.emitted();
    })

    it("should render a div for each tag", () => {
        let tags = wrapper.findAll(".ti-tag-center");
        assert(tags.length == testTags.length, "Wrong number of tags");
        for(let i=0; i < testTags.length; i++) {
            assert(tags.at(i).is('div'), "button not a div");
            assert(tags.at(i).text() == testTags[i], "rendered tag label doesn't match test data");
        }
    })

    it("should emit a click event when the tag is clicked", () => {
        let tags = wrapper.findAll(".ti-tag-center > div");
        tags.at(0).trigger("click");
        assert(emitted["tag-click"], "click event not detected");
        assert(emitted["tag-click"].length == 1, "wrong event count");
    })

    it("should emit a tag model payload when tag is clicked", () => {
        let tags = wrapper.findAll(".ti-tag-center > div");
        tags.at(0).trigger("click");
        let firstEvent = emitted["tag-click"][0];
        let firstArg = firstEvent[0];
        assert(firstArg.text = testTags[0], "returned tag model doesn't match test data");
    })

    it("should change intermal model representation when new tag list assigned", async () => {
        assert(wrapper.vm.tagModels.length == 3);
        let newTags = ["floob", "clown", "hoohah", "doodoo"];
        wrapper.setProps({ value: newTags });
        assert(wrapper.vm.tagModels.length == newTags.length);
    })

})
