import { faCheckCircle, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import StatusGroupFilter, { type StatusGroup } from "./StatusGroupFilter.vue";

const GROUPS: StatusGroup[] = [
    { key: "active", label: "Active", icon: faSpinner, color: "yellow" },
    { key: "finished", label: "Finished", icon: faCheckCircle, color: "green" },
];

function mountTarget(props: Partial<{ activeGroup: string; showLabels: boolean }> = {}) {
    return mount(StatusGroupFilter as object, {
        props: { groups: GROUPS, noun: "items", ...props },
        global: getLocalVue(),
    });
}

describe("StatusGroupFilter", () => {
    it("shows one button per group, with labels only when asked", () => {
        const iconOnly = mountTarget();
        expect(iconOnly.findAll("button")).toHaveLength(2);
        expect(iconOnly.find("[data-status-group='active'] span").exists()).toBe(false);
        const labelled = mountTarget({ showLabels: true });
        expect(labelled.find("[data-status-group='active'] span").text()).toBe("Active");
        expect(labelled.find("[data-status-group='finished'] span").text()).toBe("Finished");
    });

    it("emits the clicked group, or undefined when the active group is clicked again", async () => {
        const wrapper = mountTarget({ activeGroup: "active" });
        await wrapper.find("[data-status-group='finished']").trigger("click");
        await wrapper.find("[data-status-group='active']").trigger("click");
        expect(wrapper.emitted("update:active-group")).toEqual([["finished"], [undefined]]);
    });

    it("marks the active group pressed and names the action in its title", () => {
        const wrapper = mountTarget({ activeGroup: "active" });
        const active = wrapper.find("[data-status-group='active']");
        expect(active.attributes("aria-pressed")).toBe("true");
        expect(active.attributes("data-title")).toBe("Clear active items");
        expect(wrapper.find("[data-status-group='finished']").attributes("data-title")).toBe(
            "Show only finished items",
        );
    });
});
