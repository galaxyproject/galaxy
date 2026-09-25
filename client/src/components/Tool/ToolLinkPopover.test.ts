import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import ToolLinkPopover from "./ToolLinkPopover.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

function mountPopover(props: Record<string, unknown> = {}) {
    const wrapper = shallowMount(ToolLinkPopover as object, {
        props: { target: "step-icon-0", toolId: "cat1", toolVersion: "1.0.0", ...props },
    });
    return wrapper.findComponent(GPopover);
}

describe("ToolLinkPopover", () => {
    it("lets keyboard users reach the tool link when its trigger can take focus", () => {
        const popover = mountPopover({ interactive: true });

        expect(popover.props("interactive")).toBe(true);
        expect(popover.props("ariaLabel")).toBe("Tool");
    });

    it("stays a tooltip unless the call site opts in", () => {
        expect(mountPopover().props("interactive")).toBe(false);
    });
});
