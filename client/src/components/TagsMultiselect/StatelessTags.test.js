import { mount } from "@vue/test-utils";
import { useToast } from "composables/toast";
import { getLocalVue } from "tests/jest/helpers";
import { computed } from "vue";

import { normalizeTag, useUserTagsStore } from "@/stores/userTagsStore";

import StatelessTags from "./StatelessTags";

const autocompleteTags = ["name:named_user_tag", "abc", "my_tag"];
const toggleButton = ".toggle-button";

const localVue = getLocalVue();

const mountWithProps = (props) => {
    return mount(StatelessTags, {
        propsData: props,
        localVue,
    });
};

jest.mock("@/stores/userTagsStore");
const onNewTagSeenMock = jest.fn((tag) => tag);
useUserTagsStore.mockReturnValue({
    userTags: computed(() => autocompleteTags),
    onNewTagSeen: onNewTagSeenMock,
    onTagUsed: jest.fn(),
    onMultipleNewTagsSeen: jest.fn(),
});

function normalize(tag) {
    return tag.replace(/^#/, "name:");
}

normalizeTag.mockImplementation(normalize);

jest.mock("composables/toast");
const warningMock = jest.fn((message, title) => {
    return { message, title };
});
useToast.mockReturnValue({
    warning: warningMock,
});

const selectors = {
    multiselect: ".headless-multiselect",
    options: ".headless-multiselect__option",
    input: "fieldset input",
};

describe("StatelessTags", () => {
    it("shows tags", () => {
        const wrapper = mountWithProps({
            value: ["tag_1", "tag_2", "tags:tag_3"],
            disabled: true,
        });

        expect(wrapper.find(".tag").exists()).toBe(true);

        const tags = wrapper.findAll(".tag");
        expect(tags.length).toBe(3);
        expect(tags.at(0).text()).toBe("tag_1");
        expect(tags.at(1).text()).toBe("tag_2");
        expect(tags.at(2).text()).toBe("tags:tag_3");
    });

    it("formats named tags", () => {
        const wrapper = mountWithProps({
            value: ["name:tag_1", "tag_2", "name:tag_3"],
            disabled: true,
        });

        const tags = wrapper.findAll(".tag");
        expect(tags.at(0).text()).toBe("#tag_1");
        expect(tags.at(1).text()).toBe("tag_2");
        expect(tags.at(2).text()).toBe("#tag_3");
    });

    it("shows autocomplete options", async () => {
        const wrapper = mountWithProps({
            disabled: false,
        });

        wrapper.find(toggleButton).trigger("click");
        await wrapper.vm.$nextTick();

        const multiselect = wrapper.find(selectors.multiselect);

        await wrapper.vm.$nextTick();
        const options = multiselect.findAll(selectors.options);

        const visibleOptions = options.filter((option) => option.isVisible());

        expect(visibleOptions.length).toBe(autocompleteTags.length);

        visibleOptions.wrappers.forEach((option, i) => {
            expect(normalize(option.text())).toContain(autocompleteTags[i]);
        });
    });

    it("adds new tags", async () => {
        const wrapper = mountWithProps({
            disabled: false,
        });

        wrapper.find(toggleButton).trigger("click");
        await wrapper.vm.$nextTick();
        const multiselect = wrapper.find(selectors.multiselect);
        await multiselect.find(selectors.input).setValue("new_tag");
        await wrapper.vm.$nextTick();
        multiselect.find(selectors.options).trigger("click");
        await wrapper.vm.$nextTick();

        expect(onNewTagSeenMock.mock.calls.length).toBe(1);
        expect(onNewTagSeenMock.mock.results[0].value).toBe("new_tag");
    });

    it("warns about not allowed tags", async () => {
        const wrapper = mountWithProps({
            disabled: false,
        });

        wrapper.find(toggleButton).trigger("click");
        await wrapper.vm.$nextTick();
        const multiselect = wrapper.find(selectors.multiselect);
        await multiselect.find(selectors.input).setValue(":illegal_tag");
        await wrapper.vm.$nextTick();

        const option = multiselect.find(selectors.options);
        expect(option.classes()).toContain("invalid");

        option.trigger("click");
        await wrapper.vm.$nextTick();

        expect(warningMock.mock.calls.length).toBe(1);
        expect(warningMock.mock.results[0].value.title).toBe("Invalid Tag");
    });

    it("hides too many tags", async () => {
        const wrapper = mountWithProps({
            value: ["tag_1", "tag_2", "tag_3", "tag_4", "tag_5", "tag_6"],
            disabled: true,
            useToggleLing: true,
            maxVisibleTags: 4,
        });

        const tags = wrapper.findAll(".tag");
        expect(tags.length).toBe(4);

        const showMoreLink = wrapper.find(".toggle-link");
        expect(showMoreLink.text()).toContain("2");
    });
});
