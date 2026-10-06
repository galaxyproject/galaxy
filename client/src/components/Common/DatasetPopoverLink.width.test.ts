import { createTestingPinia } from "@pinia/testing";
import { compileStyle, parse } from "@vue/compiler-sfc";
import { mount, RouterLinkStub, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { readFileSync } from "fs";
import { resolve } from "path";
import { afterEach, describe, expect, it, vi } from "vitest";

import DatasetPopoverLink from "./DatasetPopoverLink.vue";

// Vitest does not load SFC styles, so compile this component's scoped CSS the way the build does.
function injectScopedStyles() {
    const filename = resolve(__dirname, "DatasetPopoverLink.vue");
    const { descriptor } = parse(readFileSync(filename, "utf-8"), { filename });
    const id = (DatasetPopoverLink as { __scopeId?: string }).__scopeId ?? "";
    const style = document.createElement("style");
    style.textContent = descriptor.styles
        .map((block) => compileStyle({ source: block.content, filename, id, scoped: block.scoped }).code)
        .join("\n");
    document.head.appendChild(style);
    return style;
}

describe("DatasetPopoverLink", () => {
    let wrapper: VueWrapper | undefined;
    let style: HTMLStyleElement | undefined;

    afterEach(() => {
        wrapper?.unmount();
        style?.remove();
    });

    it("caps the width of the popover content after it moves to the document body", async () => {
        style = injectScopedStyles();
        wrapper = mount(DatasetPopoverLink as object, {
            props: { datasetId: "dataset-id" },
            global: {
                plugins: [createTestingPinia({ createSpy: vi.fn })],
                stubs: { RouterLink: RouterLinkStub },
            },
            attachTo: document.body,
        });
        await flushPromises();

        const content = document.querySelector<HTMLElement>(".dataset-details-popover");
        expect(content).not.toBeNull();
        expect(wrapper.element.contains(content)).toBe(false);
        expect(getComputedStyle(content!).maxWidth).toBe("420px");
    });
});
