import { faCheck, faTimes } from "@fortawesome/free-solid-svg-icons";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import IncludedBadge from "./IncludedBadge.vue";

function mountBadge(included: boolean) {
    return mount(IncludedBadge, { props: { itemName: "hidden", included } });
}

describe("IncludedBadge", () => {
    it("shows the item name with a check in the primary color when included", () => {
        const wrapper = mountBadge(true);

        const badge = wrapper.get(".g-badge");
        expect(badge.classes()).toContain("g-primary");
        expect(badge.text()).toBe("hidden");
        expect(badge.get("svg").attributes("data-icon")).toBe(faCheck.iconName);
    });

    it("shows the item name with a cross in the secondary color when not included", () => {
        const wrapper = mountBadge(false);

        const badge = wrapper.get(".g-badge");
        expect(badge.classes()).toContain("g-secondary");
        expect(badge.text()).toBe("hidden");
        expect(badge.get("svg").attributes("data-icon")).toBe(faTimes.iconName);
    });

    it("follows a change of the included prop", async () => {
        const wrapper = mountBadge(false);

        await wrapper.setProps({ included: true });

        const badge = wrapper.get(".g-badge");
        expect(badge.classes()).toContain("g-primary");
        expect(badge.get("svg").attributes("data-icon")).toBe(faCheck.iconName);
    });
});
