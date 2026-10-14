import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import ToolDetailsButton from "./ToolDetailsButton.vue";

// Translates only what a test asks for, so the other assertions see the source strings.
const translations = vi.hoisted(() => ({}) as Record<string, string>);
vi.mock("@/utils/localization", async (importOriginal) => {
    const actual = await importOriginal<{ localize: (text: string) => string }>();
    const localize = (text: string) => translations[text] ?? actual.localize(text);
    return { ...actual, default: localize, localize };
});

const localVue = getLocalVue();

let wrapper: VueWrapper | undefined;

afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
    Object.keys(translations).forEach((text) => delete translations[text]);
});

async function mountButton(props: Record<string, unknown> = {}, slots: Record<string, string> = {}) {
    wrapper = mount(ToolDetailsButton as object, {
        attachTo: document.body,
        props: { toolId: "cat1", toolVersion: "1.0.0", ...props },
        slots,
        // ToolLink fetches the tool's name, which these tests don't need.
        global: { ...localVue, stubs: { ...localVue.stubs, ToolLink: true } },
    });
    // GPopover binds to its target on the tick after mounting.
    await nextTick();
    await nextTick();
    return wrapper.find("button").element as HTMLButtonElement;
}

// Queried off the document, since the popover relocates out of the wrapper.
function popover() {
    const el = document.body.querySelector<HTMLElement>(".popover");
    if (!el) {
        throw new Error("popover element not found");
    }
    return el;
}

describe("ToolDetailsButton", () => {
    it("renders a focusable button named for keyboard and screen reader users", async () => {
        const button = await mountButton();

        expect(button.getAttribute("type")).toBe("button");
        expect(button.getAttribute("aria-label")).toBe("Tool details");
        expect(button.classList.value).toBe("g-link g-dark g-thin");
        expect(button.tabIndex).toBe(0);
        expect(button.querySelector("svg.fa-info-circle.fa-sm")).not.toBeNull();
    });

    it("localizes the button's accessible name", async () => {
        translations["Tool details"] = "Werkzeugdetails";

        const button = await mountButton();

        expect(button.getAttribute("aria-label")).toBe("Werkzeugdetails");
    });

    it("takes the caller's id and icon", async () => {
        const button = await mountButton({ id: "step-1" }, { default: "<i class='custom-icon' />" });

        expect(button.id).toBe("step-1");
        expect(button.querySelector(".custom-icon")).not.toBeNull();
        expect(button.querySelector("svg.fa-info-circle")).toBeNull();
    });

    it("controls a tool dialog that sits next to it in the page", async () => {
        const button = await mountButton();
        const dialog = popover();

        expect(button.getAttribute("aria-haspopup")).toBe("dialog");
        expect(button.getAttribute("aria-expanded")).toBe("false");
        expect(button.getAttribute("aria-controls")).toBe(dialog.id);
        expect(dialog.getAttribute("role")).toBe("dialog");
        expect(dialog.getAttribute("aria-label")).toBe("Tool");
        expect(button.nextElementSibling?.classList.contains("g-popover-host")).toBe(true);
    });

    it("opens the popover with the tool link on keyboard focus", async () => {
        const button = await mountButton();

        button.focus();
        await nextTick();

        expect(button.getAttribute("aria-expanded")).toBe("true");
        expect(popover().style.display).not.toBe("none");
        expect(popover().querySelector("tool-link-stub")?.getAttribute("toolid")).toBe("cat1");
    });
});
