import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import GFormInput from "./components/Form/GFormInput.vue";
import GFormLabel from "./components/Form/GFormLabel.vue";
import GButton from "./components/GButton.vue";
import GDropdownItem from "./components/GDropdownItem.vue";
import GLink from "./components/GLink.vue";
import GTab from "./components/GTab.vue";
import GTable from "./components/GTable.vue";
import GTabs from "./components/GTabs.vue";

/**
 * Class names a consumer styles against, so they are public API: the Tool Shed's shed.css and a few
 * of its scoped :deep() rules restyle these. Renaming one breaks that styling with nothing else failing,
 * so a change here needs the same change in the consumers (see README.md).
 */
describe("galaxy-ui public class names", () => {
    it("GTabs: tabs, nav-tabs, nav-link, active, tab-content", async () => {
        const wrapper = mount({
            components: { GTabs, GTab },
            template: `<GTabs><GTab title="One">one</GTab><GTab title="Two">two</GTab></GTabs>`,
        });
        await flushPromises();

        expect(wrapper.find(".tabs .nav-tabs .nav-link.active").exists()).toBe(true);
        expect(wrapper.find(".tabs .tab-content").exists()).toBe(true);
    });

    it("GTable: g-table-container, g-table, table, table-bordered, g-table-compact, g-table-sorted", () => {
        const wrapper = mount(GTable as object, {
            props: {
                items: [{ name: "a" }],
                fields: [{ key: "name", sortable: true }],
                sortBy: "name",
                bordered: true,
                compact: true,
            },
        });

        expect(wrapper.find(".g-table-container .g-table.table.table-bordered.g-table-compact").exists()).toBe(true);
        expect(wrapper.find("thead th.g-table-sorted").exists()).toBe(true);
    });

    it("GFormLabel and GFormInput: g-form-label, label-text, g-form-input", () => {
        const wrapper = mount({
            components: { GFormLabel, GFormInput },
            template: `<GFormLabel title="Name"><GFormInput /></GFormLabel>`,
        });

        expect(wrapper.find(".g-form-label .label-text").exists()).toBe(true);
        expect(wrapper.find("input.g-form-input").exists()).toBe(true);
    });

    it("GButton, GLink and GDropdownItem: g-button, g-transparent, g-link, dropdown-item", () => {
        expect(mount(GButton as object, { props: { transparent: true } }).classes()).toEqual(
            expect.arrayContaining(["g-button", "g-transparent"]),
        );
        expect(mount(GLink as object, { props: { href: "#" } }).classes()).toContain("g-link");
        expect(
            mount(GDropdownItem as object, { props: { href: "#" } })
                .find(".dropdown-item")
                .exists(),
        ).toBe(true);
    });
});
