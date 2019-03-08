/* global expect */

import Vuex from "vuex";
import { mount, createLocalVue } from "@vue/test-utils";
import Tags from "./Tags";
import _l from "utils/localization";
import store from "../../store";
import { TagService } from "./tagService";
import { createTag } from "./model";

const localVue = createLocalVue();
localVue.filter("localize", value => _l(value));
localVue.use(Vuex);

describe("Tags/Tags.vue", () => {

    let id = "testId",
        itemClass = "TestObject",
        context = "testing",
        tagService, 
        wrapper,
        emitted,
        startingTags = ["a","b","c"],
        storeKey = "testingTagSet",
        acResults = [];

    let clickFirstTag = () => {
        if (wrapper) {
            let firstTag = wrapper.find(".ti-tag-center > div");
            firstTag.trigger("click");
        } else {
            console.log("missing tag");
        }
    }

    // Run bef  oreEach as async so the lifecycle methods can run
    beforeEach(async () => {

        // TODO: this mocking mechanism is no good.
 
        tagService = new TagService({ id, itemClass, context });
        
        tagService.save = async function(tag) {
            return null;
        }
        
        tagService.delete = async function(tag) {
            return null;
        }
        
        tagService.autocomplete = async function() {
            console.log("mock");
            return acResults.map(createTag);
        }


        // Mount the tags with sample props

        wrapper = mount(Tags, {
            store,
            localVue,
            propsData: {
                tags: startingTags,
                storeKey,
                tagService
            }
        });

        emitted = wrapper.emitted();

        // Waits for lifecycle handlers to execute
        await wrapper.vm.$nextTick();
    })

    afterEach(() => {
        tagService = null;
    })

    it("should display the tags I give it", async () => {
        let tags = wrapper.findAll(".ti-tag-center .tag-name");
        expect(tags.length).to.equal(3);
        expect(tags.at(0).text()).to.equal(startingTags[0]);
    })

    it("should put the initialized tags into the store at initialization", async () => {
        let storedTags = store.getters.getTagsById(storeKey);     
        expect(storedTags.length).to.equal(3);
        startingTags.forEach((tag, i) => {
            expect(tag).to.equal(storedTags[i]);
        })
    })

    it("should respond to click events on the tags", async () => {
        clickFirstTag();
        assert(emitted["tag-click"], "click event not detected");
        assert(emitted["tag-click"].length == 1, "wrong event count");
    })

    it("should reflect changes in the store", async () => {
        
        let newTags = ["asdfadsadf", "gfhjfghjf"];
        store.dispatch("updateTags", { key: storeKey, tags: newTags });

        // TODO: figure out how to make the computed observableTags
        // prop update when the store does

        // Doesn't work
        // wrapper.vm.$forceUpdate();
        // await wrapper.vm.$nextTick();

        // works, but is lame
        wrapper.setProps({ storeKey: "thisisgarbage" });
        wrapper.setProps({ storeKey });
        
        let observed = wrapper.vm.observedTags;
        expect(observed.length).to.equal(newTags.length);
        observed.forEach((tagLabel, i) => {
            expect(newTags[i]).to.equal(tagLabel);
        })

        let renderedTags = wrapper.findAll(".tag-name");
        console.log(renderedTags, renderedTags.length);
    })

    xit("updating tag search should generate autocomplete items", async () => {

        let acResults = ["a","b","c","d","e","f"];
        tagService._autocompleteResults = acResults;
        await wrapper.vm.$nextTick();
        
        tagService.autocompleteSearchText = "foo";
        await wrapper.vm.$nextTick();
        expect(wrapper.vm.autocompleteItems.length).to.equal(acResults.length);

        // // wrapper.vm.updateTagSearch("foo");
        // // expect(wrapper.vm.autocompleteItems.length).to.equal(acResults.length);
        // done();
    })

});
