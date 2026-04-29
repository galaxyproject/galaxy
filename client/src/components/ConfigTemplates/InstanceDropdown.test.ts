import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import InstanceDropdown from "./InstanceDropdown.vue";

const localVue = getLocalVue(true);

describe("InstanceDropdown", () => {
    it("should render a drop down without upgrade if upgrade unavailable as an option", async () => {
        const wrapper = shallowMount(InstanceDropdown as object, {
            props: {
                prefix: "file-source",
                name: "my cool instance",
                routeEdit: "/object_store_instance/edit",
                routeUpgrade: "/object_store_instance/upgrade",
                isUpgradable: false,
            },
            global: localVue,
        });
        const menu = wrapper.find(".dropdown-menu");
        const links = menu.findAll("button.dropdown-item");
        expect(links.length).toBe(3);
    });

    it("should render a drop down with upgrade if upgrade available as an option", async () => {
        const wrapper = shallowMount(InstanceDropdown as object, {
            props: {
                prefix: "file-source",
                name: "my cool instance",
                routeEdit: "/object_store_instance/edit",
                routeUpgrade: "/object_store_instance/upgrade",
                isUpgradable: true,
            },
            global: localVue,
        });
        const menu = wrapper.find(".dropdown-menu");
        const links = menu.findAll("button.dropdown-item");
        expect(links.length).toBe(4);
    });
});
