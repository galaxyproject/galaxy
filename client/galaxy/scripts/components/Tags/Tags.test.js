/* global expect */

import Vuex from "vuex";
import { mount, createLocalVue } from "@vue/test-utils";
import Tags from "./Tags";
import _l from "utils/localization";
import store from "../../store";
import { TagService } from "./tagService";
import { createTag } from "./model";

describe("Tags/Tags.vue", () => {
    const localVue = createLocalVue();
    localVue.filter("localize", value => _l(value));
    localVue.use(Vuex);

    let id = "testId",
        itemClass = "TestObject",
        context = "testing",
        tagService,
        wrapper,
        emitted,
        startingTags = ["a", "b", "c"],
        storeKey = "testingTagSet";

    let clickFirstTag = () => {
        if (wrapper) {
            let firstTag = wrapper.find(".ti-tag-center > div");
            firstTag.trigger("click");
        } else {
            console.log("missing tag");
        }
    };

    // Run before each as async so the lifecycle methods can run
    beforeEach(async () => {
        // TODO: this mocking mechanism is no good.

        tagService = new TagService({ id, itemClass, context });

        tagService.save = async function(tag) {
            return createTag(tag);
        };

        tagService.delete = async function(tag) {
            return createTag(tag);
        };

        tagService.autocomplete = async function(txt) {
            return [txt].map(createTag);
        };

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
    });

    afterEach(() => {
        tagService = null;
    });

    it("should display the tags I give it", async () => {
        let tags = wrapper.findAll(".ti-tag-center .tag-name");
        expect(tags.length).to.equal(3);
        expect(tags.at(0).text()).to.equal(startingTags[0]);
    });

    it("should put the initialized tags into the store at initialization", async () => {
        let storedTags = store.getters.getTagsById(storeKey);
        expect(storedTags.length).to.equal(3);
        startingTags.forEach((tag, i) => {
            expect(tag).to.equal(storedTags[i]);
        });
    });

    it("should respond to click events on the tags", async () => {
        clickFirstTag();
        assert(emitted["tag-click"], "click event not detected");
        assert(emitted["tag-click"].length == 1, "wrong event count");
    });

    it("should reflect changes in the store", async () => {
        let newTags = ["asdfadsadf", "gfhjfghjf"];
        store.dispatch("updateTags", { key: storeKey, tags: newTags });

        // TODO: figure out how to make the computed observableTags
        // prop update when the store does. This works in the real code,
        // but does not update in this test environment. The following
        // brute force mechanism of changing a different dependency works
        // and effectively recalculates the computed value, but it should
        // not be necessary
        wrapper.setProps({ storeKey: "thisshouldbeunnecessary" });
        wrapper.setProps({ storeKey });

        let observed = wrapper.vm.observedTags;
        expect(observed.length).to.equal(newTags.length);
        observed.forEach((tagLabel, i) => {
            expect(newTags[i]).to.equal(tagLabel);
        });
    });

    describe("autocomplete list", () => {
        let subscription;

        afterEach(() => {
            if (subscription) {
                subscription.unsubscribe();
            }
        });

        it("should generate autocomplete items when you set the search text", done => {
            let sampleTxt = "floobar";
            subscription = tagService.autocompleteOptions.subscribe(results => {
                expect(results.length).equal(1);
                results.forEach(r => {
                    expect(r.text).equal(sampleTxt);
                });
                done();
            });
            tagService.autocompleteSearchText = sampleTxt;
        });

        it("should debounce autocomplete requests", done => {
            let sampleTxt = "floobar";
            subscription = tagService.autocompleteOptions.subscribe(results => {
                expect(results.length).equal(1);
                results.forEach(r => {
                    expect(r.text).equal(sampleTxt);
                });
                done();
            });
            tagService.autocompleteSearchText = "foo";
            tagService.autocompleteSearchText = sampleTxt;
        });
    });
});
