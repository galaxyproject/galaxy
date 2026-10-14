import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { copy } from "@/utils/clipboard";

import CopyToClipboard from "./CopyToClipboard.vue";

vi.mock("@/utils/clipboard", () => ({
    copy: vi.fn(),
}));

const TEXT = "secret-api-key" as const;
const MESSAGE = "Key was copied to clipboard" as const;
const TITLE = "Copy key" as const;

function mountComponent(props: Record<string, unknown> = {}) {
    return mount(CopyToClipboard as object, {
        props: { text: TEXT, message: MESSAGE, ...props },
        global: getLocalVue(),
    });
}

describe("CopyToClipboard", () => {
    beforeEach(() => {
        vi.mocked(copy).mockClear();
    });

    it("copies the text with the message on click", async () => {
        const wrapper = mountComponent();
        await wrapper.find("button").trigger("click");
        expect(copy).toHaveBeenCalledOnce();
        expect(copy).toHaveBeenCalledWith(TEXT, MESSAGE);
    });

    it("renders the title on the button", () => {
        const wrapper = mountComponent({ title: TITLE });
        expect(wrapper.find("button").attributes("title")).toBe(TITLE);
    });

    it("has a default title", () => {
        const wrapper = mountComponent();
        expect(wrapper.find("button").attributes("title")).toBe("Copy to clipboard");
    });

    it("is transparent by default", () => {
        const wrapper = mountComponent();
        expect(wrapper.find("button").classes()).toContain("g-transparent");
    });

    it("is not transparent when transparent is false", () => {
        const wrapper = mountComponent({ transparent: false });
        expect(wrapper.find("button").classes()).not.toContain("g-transparent");
    });
});
