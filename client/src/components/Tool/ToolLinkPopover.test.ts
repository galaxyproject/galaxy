import { shallowMount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import ToolLinkPopover from "./ToolLinkPopover.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

// Translates only what a test asks for, so the other assertions see the source strings.
const translations = vi.hoisted(() => ({}) as Record<string, string>);
vi.mock("@/utils/localization", async (importOriginal) => {
    const actual = await importOriginal<{ localize: (text: string) => string }>();
    const localize = (text: string) => translations[text] ?? actual.localize(text);
    return { ...actual, default: localize, localize };
});

function mountPopover(props: Record<string, unknown> = {}) {
    const wrapper = shallowMount(ToolLinkPopover as object, {
        props: { target: "step-icon-0", toolId: "cat1", toolVersion: "1.0.0", ...props },
    });
    return wrapper.findComponent(GPopover);
}

describe("ToolLinkPopover", () => {
    afterEach(() => {
        Object.keys(translations).forEach((text) => delete translations[text]);
    });

    it("lets keyboard users reach the tool link when its trigger can take focus", () => {
        const popover = mountPopover({ interactive: true });

        expect(popover.props("interactive")).toBe(true);
        expect(popover.props("ariaLabel")).toBe("Tool");
    });

    it("localizes the popover's accessible name", () => {
        translations["Tool"] = "Werkzeug";

        expect(mountPopover({ interactive: true }).props("ariaLabel")).toBe("Werkzeug");
    });

    it("stays a tooltip unless the call site opts in", () => {
        expect(mountPopover().props("interactive")).toBe(false);
    });
});
