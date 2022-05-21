import Vuex from "vuex";
import { mount } from "@vue/test-utils";
import Tags from "./Tags";
import { TagService } from "./tagService";
import { tagStore } from "store/tagStore";
import { getLocalVue } from "jest/helpers";

jest.mock("./tagService");

const localVue = getLocalVue();

const testStore = new Vuex.Store({
    modules: {
        tagStore,
    },
});

describe("Tags/Tags.vue", () => {
    const id = "testId";
    const itemClass = "TestObject";
    const context = "testing";
    let tagService;
    let wrapper;
    let emitted;
    const startingTags = ["a", "b", "c"];
    const storeKey = "testingTagSet";

    const clickFirstTag = () => {
        if (wrapper) {
            const firstTag = wrapper.find(".ti-tag-center > div");
            firstTag.trigger("click");
        } else {
            console.log("missing tag");
        }
    };

    // Run before each as async so the lifecycle methods can run
    beforeEach(async () => {
        // Create the (mocked, above) TagService
        tagService = new TagService({ id, itemClass, context });

        // Mount the tags with sample props

        wrapper = mount(Tags, {
            store: testStore,
            localVue,
            propsData: {
                tags: startingTags,
                storeKey,
                tagService,
            },
        });

        emitted = wrapper.emitted();

        // Waits for lifecycle handlers to execute
        await wrapper.vm.$nextTick();
    });

    afterEach(() => {
        tagService = null;
    });

    it("should display the tags I give it", async () => {
        const tags = wrapper.findAll(".ti-tag-center .tag-name");
        expect(tags.length).toBe(3);
        expect(tags.at(0).text()).toBe(startingTags[0]);
    });

    it("should put the initialized tags into the store at initialization", async () => {
        const storedTags = testStore.getters.getTagsById(storeKey);
        expect(storedTags.length).toBe(3);
        startingTags.forEach((tag, i) => {
            expect(tag).toBe(storedTags[i]);
        });
    });

    it("should respond to click events on the tags", async () => {
        clickFirstTag();
        expect(emitted["tag-click"]).toBeTruthy();
        expect(emitted["tag-click"].length == 1).toBeTruthy();
    });

    it("should reflect changes in the store", async () => {
        const newTags = ["asdfadsadf", "gfhjfghjf"];
        testStore.dispatch("updateTags", { key: storeKey, tags: newTags });

        await wrapper.setProps({ storeKey });

        const observed = wrapper.vm.observedTags;
        expect(observed.length).toBe(newTags.length);
        observed.forEach((tagLabel, i) => {
            expect(newTags[i]).toBe(tagLabel);
        });
    });

    describe("autocomplete list", () => {
        let subscription;

        afterEach(() => {
            if (subscription) {
                subscription.unsubscribe();
            }
        });

        it("should generate autocomplete items when you set the search text", (done) => {
            const sampleTxt = "floobar";
            subscription = tagService.autocompleteOptions.subscribe((results) => {
                expect(results.length).toBe(1);
                results.forEach((r) => {
                    expect(r.text).toBe(sampleTxt);
                });
                done();
            });
            tagService.autocompleteSearchText = sampleTxt;
        });

        it("should debounce autocomplete requests", (done) => {
            const sampleTxt = "floobar";
            subscription = tagService.autocompleteOptions.subscribe((results) => {
                expect(results.length).toBe(1);
                results.forEach((r) => {
                    expect(r.text).toBe(sampleTxt);
                });
                done();
            });
            tagService.autocompleteSearchText = "foo";
            tagService.autocompleteSearchText = sampleTxt;
        });
    });
});
