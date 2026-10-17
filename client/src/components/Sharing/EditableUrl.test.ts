import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import EditableUrl from "./EditableUrl.vue";

describe("EditableUrl", () => {
    it("submits the slug when Enter is pressed in the slug input", async () => {
        const wrapper = mount(EditableUrl, {
            props: { prefix: "https://galaxy.example/u/me/p/", slug: "my-page" },
            global: getLocalVue(),
        });
        await wrapper.get("#item-url + button").trigger("click");
        expect(wrapper.find("#item-url-text").exists()).toBe(true);

        await wrapper.get("#item-url-text input").trigger("keyup", { key: "Enter" });

        expect(wrapper.emitted("submit")).toEqual([["my-page"]]);
        expect(wrapper.find("#item-url-text").exists()).toBe(false);
    });
});
