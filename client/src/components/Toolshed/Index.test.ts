import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import Index from "./Index.vue";

const localVue = getLocalVue();

function mountIndex() {
    return mount(Index as object, {
        global: { ...localVue, stubs: { ...localVue.stubs, InstalledList: true, SearchList: true } },
    });
}

describe("Toolshed Index", () => {
    it("offers a named choice between all and installed repositories", () => {
        const wrapper = mountIndex();
        const group = wrapper.find("[role=radiogroup]");
        expect(group.attributes("aria-label")).toBe("Repositories to list");
        const radios = group.findAll<HTMLInputElement>("input[type=radio]");
        expect(radios.map((radio) => radio.element.labels?.[0]?.textContent?.trim())).toEqual([
            "Search All",
            "Installed Only",
        ]);
        expect(radios.map((radio) => radio.element.checked)).toEqual([true, false]);
        expect(wrapper.find("search-list-stub").exists()).toBe(true);
    });

    it("lists installed repositories once Installed Only is chosen", async () => {
        const wrapper = mountIndex();
        await wrapper.findAll("input[type=radio]")[1]!.setValue(true);
        expect(wrapper.find("installed-list-stub").exists()).toBe(true);
        expect(wrapper.find("search-list-stub").exists()).toBe(false);
    });
});
