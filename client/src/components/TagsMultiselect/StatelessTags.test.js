import { getLocalVue } from "tests/jest/helpers";
import { mount } from "@vue/test-utils";
import { useUserTags } from "composables/user";
import { useToast } from "composables/toast";
import { computed } from "vue";
import StatelessTags from "./StatelessTags";

const autocompleteTags = ["#named_user_tag", "abc", "my_tag"];

const localVue = getLocalVue();

const mountWithProps = (props) => {
    return mount(StatelessTags, {
        propsData: props,
        localVue,
    });
};

jest.mock("composables/user");
const addLocalTagMock = jest.fn((tag) => tag);
useUserTags.mockReturnValue({
    userTags: computed(() => autocompleteTags),
    addLocalTag: addLocalTagMock,
});

jest.mock("composables/toast");
const warningMock = jest.fn((message, title) => {
    return { message, title };
});
useToast.mockReturnValue({
    warning: warningMock,
});

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

        const multiselect = wrapper.find(".multiselect");

        multiselect.find("button").trigger("click");
        await wrapper.vm.$nextTick();

        const options = multiselect.findAll(".multiselect-option");
        const visibleOptions = options.filter((option) => option.isVisible());

        expect(visibleOptions.length).toBe(autocompleteTags.length);

        visibleOptions.wrappers.forEach((option, i) => {
            expect(option.text()).toContain(autocompleteTags[i]);
        });
    });

    it("adds new tags", async () => {
        const wrapper = mountWithProps({
            disabled: false,
        });

        const multiselect = wrapper.find(".multiselect");

        multiselect.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        await multiselect.find("input").setValue("new_tag");
        await wrapper.vm.$nextTick();
        multiselect.find(".multiselect-option").trigger("click");
        await wrapper.vm.$nextTick();

        expect(addLocalTagMock.mock.calls.length).toBe(1);
        expect(addLocalTagMock.mock.results[0].value).toBe("new_tag");
    });

    it("warns about not allowed tags", async () => {
        const wrapper = mountWithProps({
            disabled: false,
        });

        const multiselect = wrapper.find(".multiselect");

        multiselect.find("button").trigger("click");
        await wrapper.vm.$nextTick();
        await multiselect.find("input").setValue(":illegal_tag");
        await wrapper.vm.$nextTick();

        const option = multiselect.find(".multiselect-option");
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
