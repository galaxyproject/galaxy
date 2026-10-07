import { getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import { DOMWrapper, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Toast } from "@/composables/toast";

import StatelessTags from "./StatelessTags.vue";

const autocompleteTags = ["name:named_user_tag", "abc", "my_tag"];
const toggleButton = ".toggle-button";

const localVue = getLocalVue();

// The underlying HeadlessMultiselect teleports its options popup to `#app`. Recreate
// that root so the teleported content lands in the DOM, mirroring how the real app
// mounts; it's not a descendant of the wrapper, so it's queried via document.body.
let appRoot;

const mountWithProps = (props) => {
    return mount(StatelessTags, {
        props: props,
        global: localVue,
        attachTo: appRoot,
    });
};

const onNewTagSeenMock = vi.fn((tag) => tag);

function normalize(tag) {
    return tag.replace(/^#/, "name:");
}

vi.mock("@/stores/userTagsStore", () => ({
    useUserTagsStore: vi.fn(() => ({
        userTags: autocompleteTags,
        onNewTagSeen: onNewTagSeenMock,
        onTagUsed: vi.fn(),
        onMultipleNewTagsSeen: vi.fn(),
    })),
    normalizeTag: vi.fn((tag) => normalize(tag)),
}));

vi.mock("@/composables/toast");

const toastWarning = vi.mocked(Toast.warning);

const selectors = {
    multiselect: ".headless-multiselect",
    options: ".headless-multiselect__option",
    input: "fieldset input",
};

describe("StatelessTags", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        onNewTagSeenMock.mockClear();
        toastWarning.mockClear();
        appRoot = document.createElement("div");
        appRoot.id = "app";
        document.body.appendChild(appRoot);
    });

    afterEach(() => {
        appRoot.remove();
    });

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

        await wrapper.vm.$nextTick();
        // The options popup is teleported to #app, so it's not a descendant of the
        // wrapper -- query the DOM directly for it.
        const options = new DOMWrapper(document.body).findAll(selectors.options);

        const visibleOptions = options.filter((option) => option.isVisible());

        expect(visibleOptions.length).toBe(autocompleteTags.length);

        visibleOptions.forEach((option, i) => {
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
        new DOMWrapper(document.body).find(selectors.options).trigger("click");
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

        const option = new DOMWrapper(document.body).find(selectors.options);
        expect(option.classes()).toContain("invalid");

        option.trigger("click");
        await wrapper.vm.$nextTick();

        expect(toastWarning).toHaveBeenCalledTimes(1);
        expect(toastWarning).toHaveBeenCalledWith(expect.any(String), "Invalid Tag");
    });

    it("hides too many tags", async () => {
        const wrapper = mountWithProps({
            value: ["tag_1", "tag_2", "tag_3", "tag_4", "tag_5", "tag_6"],
            disabled: true,
            useToggleLing: true,
            maxVisibleTags: 4,
        });

        const tags = wrapper.findAll(".tag").filter((w) => !w.element.closest(".g-tooltip"));
        expect(tags.length).toBe(4);

        const showMoreLink = wrapper.find(".toggle-link");
        expect(showMoreLink.text()).toContain("2");
    });
});
