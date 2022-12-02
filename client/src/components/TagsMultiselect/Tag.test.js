import { getLocalVue } from "jest/helpers";
import { mount } from "@vue/test-utils";
import Tag from "./Tag";

const localVue = getLocalVue();

const mountWithProps = (props) => {
    return mount(Tag, {
        propsData: props,
        localVue,
    });
};

describe("Tag", () => {
    it("displays it's option", () => {
        {
            const wrapper = mountWithProps({ option: "my_tag" });
            const tag = wrapper.find(".tag");
            expect(tag.text()).toBe("my_tag");
        }

        {
            const wrapper = mountWithProps({ option: "a_longer_tag_name" });
            const tag = wrapper.find(".tag");
            expect(tag.text()).toBe("a_longer_tag_name");
        }
    });

    it("shows it's clickable", async () => {
        const wrapper = mountWithProps({ option: "my_tag" });
        const tag = wrapper.find(".tag");

        expect(tag.classes()).not.toContain("clickable");

        tag.setProps({ clickable: true });
        await wrapper.vm.$nextTick();

        expect(tag.classes()).toContain("clickable");
    });

    it("can be clicked", async () => {
        const wrapper = mountWithProps({ option: "my_tag", clickable: true });
        const tag = wrapper.find(".tag");

        expect(tag.classes()).toContain("clickable");

        tag.trigger("click");
        await wrapper.vm.$nextTick();

        expect(tag.emitted().click).toBeTruthy();
        expect(tag.emitted().click.length).toBe(1);
        expect(tag.emitted().click[0]).toEqual(["my_tag"]);

        tag.trigger("click");
        await wrapper.vm.$nextTick();

        expect(tag.emitted().click.length).toBe(2);
        expect(tag.emitted().click).toStrictEqual([["my_tag"], ["my_tag"]]);
    });

    it("changes appearance when editable", async () => {
        const wrapper = mountWithProps({ option: "my_tag" });
        const tag = wrapper.find(".tag");

        expect(tag.classes()).not.toContain("editable");
        expect(tag.find(".tag-delete-button").exists()).not.toBe(true);

        tag.setProps({ editable: true });
        await wrapper.vm.$nextTick();

        expect(tag.classes()).toContain("editable");
        expect(tag.find(".tag-delete-button").exists()).toBe(true);
    });

    it("can be deleted", async () => {
        const wrapper = mountWithProps({ option: "my_tag", editable: true });
        const tag = wrapper.find(".tag");

        expect(tag.find(".tag-delete-button").exists()).toBe(true);

        tag.find(".tag-delete-button").trigger("click");
        await wrapper.vm.$nextTick();

        expect(tag.emitted().deleted).toBeTruthy();
        expect(tag.emitted().deleted.length).toBe(1);
        expect(tag.emitted().deleted[0]).toEqual(["my_tag"]);

        expect(tag.emitted().click).toBeFalsy();
    });

    it("displays named tags bold", () => {
        {
            const wrapper = mountWithProps({ option: "my_tag" });
            const span = wrapper.find(".tag span");
            expect(span.classes()).not.toContain("font-weight-bold");
        }

        {
            const wrapper = mountWithProps({ option: "#named_tag" });
            const span = wrapper.find(".tag span");
            expect(span.classes()).toContain("font-weight-bold");
        }
    });
});
