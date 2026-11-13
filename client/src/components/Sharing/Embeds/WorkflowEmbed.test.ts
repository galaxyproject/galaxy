import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { copy } from "@/utils/clipboard";

import WorkflowEmbed from "./WorkflowEmbed.vue";

vi.mock("@/utils/clipboard", () => ({ copy: vi.fn() }));

describe("WorkflowEmbed", () => {
    it("shows the embed code in a read-only GFormInput and copies it", async () => {
        const wrapper = mount(WorkflowEmbed as object, {
            props: { id: "workflow-id" },
            global: { ...getLocalVue(), stubs: { WorkflowPublished: true, ZoomControl: true } },
        });
        const embedInput = wrapper.get("input.embed-code-input");
        expect(embedInput.classes()).toContain("g-form-input");
        expect(embedInput.attributes("readonly")).toBeDefined();
        const embedCode = (embedInput.element as HTMLInputElement).value;
        expect(embedCode).toMatch(/^<iframe .*widgets\/workflows\/workflow-id\?.*<\/iframe>$/);

        await wrapper.get("label[for='embed-code'] button").trigger("click");
        expect(copy).toHaveBeenCalledWith(embedCode);
    });

    it("updates the embed code when a setting changes", async () => {
        const wrapper = mount(WorkflowEmbed as object, {
            props: { id: "workflow-id" },
            global: { ...getLocalVue(), stubs: { WorkflowPublished: true, ZoomControl: true } },
        });
        await wrapper.findAll(".settings input[type='checkbox']").at(0)!.setValue(true);
        expect((wrapper.get("input.embed-code-input").element as HTMLInputElement).value).toContain("heading=true");
    });
});
