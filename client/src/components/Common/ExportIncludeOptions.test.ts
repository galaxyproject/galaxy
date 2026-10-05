import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { defineComponent, reactive } from "vue";

import ExportIncludeOptions from "./ExportIncludeOptions.vue";

const localVue = getLocalVue();

// Mirrors how the export wizards bind the options, with kebab-case listeners.
const WizardLikeParent = defineComponent({
    components: { ExportIncludeOptions },
    setup() {
        const exportData = reactive({ includeFiles: true, includeDeleted: false, includeHidden: false });
        return { exportData };
    },
    template: `
        <ExportIncludeOptions
            :include-files="exportData.includeFiles"
            :include-deleted="exportData.includeDeleted"
            :include-hidden="exportData.includeHidden"
            @update:include-files="exportData.includeFiles = $event"
            @update:include-deleted="exportData.includeDeleted = $event"
            @update:include-hidden="exportData.includeHidden = $event" />
    `,
});

describe("ExportIncludeOptions", () => {
    it("updates the parent's options when switches change", async () => {
        const wrapper = mount(WizardLikeParent as object, { localVue });
        const exportData = (wrapper.vm as unknown as InstanceType<typeof WizardLikeParent>).exportData;

        await wrapper.find("input[data-test-id='include-files-checkbox']").setValue(false);
        await wrapper.find("input[data-test-id='include-deleted-checkbox']").setValue(true);
        await wrapper.find("input[data-test-id='include-hidden-checkbox']").setValue(true);

        expect(exportData).toEqual({ includeFiles: false, includeDeleted: true, includeHidden: true });
    });
});
