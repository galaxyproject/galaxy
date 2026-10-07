import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";
import type { Component } from "vue";

import type { ExtensionDetails } from "@/composables/uploadConfigurations";

import UploadSelectExtension from "./UploadSelectExtension.vue";
import UploadTableBulkExtensionHeader from "@/components/Panels/Upload/shared/UploadTableBulkExtensionHeader.vue";
import UploadTableExtensionCell from "@/components/Panels/Upload/shared/UploadTableExtensionCell.vue";

const SELECTORS = [
    { name: "upload row", component: UploadTableExtensionCell },
    { name: "bulk upload", component: UploadTableBulkExtensionHeader },
    { name: "sample sheet", component: UploadSelectExtension },
];

describe.each(SELECTORS)("Datatype guidance in $name", ({ component }) => {
    function mountSelector(value: string, extensions: ExtensionDetails[]) {
        return mount(component as Component, {
            props: {
                value,
                ...(component === UploadSelectExtension
                    ? { listExtensions: extensions }
                    : { extensions, warning: extensions.find((ext) => ext.id === value)?.upload_warning }),
            },
            global: { ...getLocalVue(), stubs: { UploadExtension: true } },
        });
    }

    it.each(["", ".gz", ".bz2"])(
        "shows guidance before selection and preserves an explicit fastq%s choice",
        async (suffix) => {
            const extension = `fastq${suffix}`;
            const recommended = `fastqsanger${suffix}`;
            const warning = `For Sanger (Phred+33) data, select ${recommended}.`;
            const extensions = ["auto", extension, recommended].map((id) => ({
                id,
                text: id,
                description: null,
                description_url: null,
                upload_warning: id === extension ? warning : null,
            }));
            const wrapper = mountSelector("auto", extensions);
            expect(wrapper.get('[role="status"]').text()).toBe("");
            expect(wrapper.emitted("input")).toBeUndefined();

            await wrapper.get(".multiselect").trigger("focus");
            await wrapper.get(".multiselect__input").setValue(extension);
            const option = wrapper.findAll(".multiselect__option").find((option) => option.text().includes(warning));
            expect(option).toBeDefined();
            expect(option!.isVisible()).toBe(true);
            expect(option!.find(".upload-datatype-warning").text()).toContain(recommended);

            await option!.trigger("click");
            expect(wrapper.emitted("input")).toEqual([[extension]]);
            await wrapper.setProps({
                value: extension,
                ...(component === UploadSelectExtension ? {} : { warning }),
            });
            expect(wrapper.get('[role="status"]').text()).toContain(warning);
            expect(wrapper.get('[role="status"] .upload-datatype-warning').isVisible()).toBe(true);

            await wrapper.setProps({
                value: recommended,
                ...(component === UploadSelectExtension ? {} : { warning: null }),
            });
            expect(wrapper.get('[role="status"]').text()).toBe("");
            wrapper.unmount();
        },
    );

    it("keeps a legacy selection and its guidance visible when disabled", () => {
        const warning = "Select fastqsanger for Sanger-encoded data.";
        const wrapper = mountSelector("fastq", [
            { id: "fastq", text: "fastq", description: null, description_url: null, upload_warning: warning },
        ]);
        return wrapper.setProps({ disabled: true }).then(() => {
            expect(wrapper.find(".multiselect--disabled").exists()).toBe(true);
            expect(wrapper.get('[role="status"]').text()).toContain(warning);
            expect(wrapper.emitted("input")).toBeUndefined();
            wrapper.unmount();
        });
    });

    it("scrolls to the highlighted choice below a multiline warning with the keyboard", async () => {
        const extensions = ["auto", "fastq", "fastqsanger"].map((id) => ({
            id,
            text: id,
            description: null,
            description_url: null,
            upload_warning: id === "fastq" ? "Use an encoding-specific type for your data." : null,
        }));
        const wrapper = mountSelector("auto", extensions);
        await wrapper.get(".multiselect").trigger("focus");
        await wrapper.get(".multiselect__input").setValue("fastq");
        const list = wrapper.get(".multiselect__content-wrapper").element as HTMLElement;
        const recommended = wrapper
            .findAll(".multiselect__option")
            .find((option) => option.text().trim() === "fastqsanger")!.element;
        vi.spyOn(list, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 0, 180, 300));
        vi.spyOn(recommended, "getBoundingClientRect").mockReturnValue(new DOMRect(0, 350, 180, 40));

        await wrapper.get(".multiselect__input").trigger("keydown", { key: "ArrowDown", keyCode: 40 });
        expect(wrapper.get(".multiselect__option--highlight").text()).toBe("fastqsanger");
        expect(list.scrollTop).toBe(90);
        await wrapper.get(".multiselect__input").trigger("keydown", { key: "Enter", keyCode: 13 });
        expect(wrapper.emitted("input")).toEqual([["fastqsanger"]]);
        vi.restoreAllMocks();
        wrapper.unmount();
    });
});
