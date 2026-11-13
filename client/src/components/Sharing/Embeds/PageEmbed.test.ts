import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { copy } from "@/utils/clipboard";

import PageEmbed from "./PageEmbed.vue";

vi.mock("@/utils/clipboard", () => ({ copy: vi.fn() }));

function mountPageEmbed() {
    return mount(PageEmbed as object, {
        props: { id: "page-id" },
        global: { ...getLocalVue(), stubs: { PageView: true } },
    });
}

describe("PageEmbed", () => {
    it("renders the width and height as number GFormInput fields", () => {
        const wrapper = mountPageEmbed();
        const [width, height] = wrapper.findAll(".dimension-controls input");
        for (const input of [width!, height!]) {
            expect(input.classes()).toContain("g-form-input");
            expect(input.attributes()).toMatchObject({ type: "number", min: "200", max: "2000", step: "50" });
        }
        expect((width!.element as HTMLInputElement).value).toBe("800");
        expect((height!.element as HTMLInputElement).value).toBe("600");
    });

    it("keeps the typed dimensions as numbers in the embed code", async () => {
        const wrapper = mountPageEmbed();
        const [width, height] = wrapper.findAll(".dimension-controls input");
        await width!.setValue("1000");
        await height!.setValue("450");

        const settings = (wrapper.vm as unknown as { settings: { width: unknown; height: unknown } }).settings;
        expect(settings.width).toBe(1000);
        expect(settings.height).toBe(450);
        expect((wrapper.get("input.embed-code-input").element as HTMLInputElement).value).toContain(
            'width="1000px" height="450px"',
        );
    });

    it("keeps the last size in the embed code while a dimension field is empty", async () => {
        const wrapper = mountPageEmbed();
        const [width] = wrapper.findAll(".dimension-controls input");
        await width!.setValue("1000");
        await width!.setValue("");

        expect((wrapper.vm as unknown as { settings: { width: unknown } }).settings.width).toBe(1000);
        expect((wrapper.get("input.embed-code-input").element as HTMLInputElement).value).toContain('width="1000px"');
    });

    it("shows the embed code in a read-only GFormInput and copies it", async () => {
        const wrapper = mountPageEmbed();
        const embedInput = wrapper.get("input.embed-code-input");
        expect(embedInput.classes()).toContain("g-form-input");
        expect(embedInput.attributes("readonly")).toBeDefined();
        const embedCode = (embedInput.element as HTMLInputElement).value;
        expect(embedCode).toMatch(/^<iframe .*widgets\/pages\/page-id\?heading=true.*<\/iframe>$/);

        await wrapper.get("label[for='embed-code'] button").trigger("click");
        expect(copy).toHaveBeenCalledWith(embedCode);
    });
});
