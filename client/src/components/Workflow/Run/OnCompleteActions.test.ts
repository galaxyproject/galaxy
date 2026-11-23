import { nth } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useFileSources } from "@/composables/fileSources";

import OnCompleteActions from "./OnCompleteActions.vue";

vi.mock("@/composables/fileSources");

const EXPORT_CONFIG = {
    target_uri: "gxfiles://export/results",
    model_store_format: "rocrate.zip",
    include_files: true,
    include_hidden: false,
    include_deleted: false,
};

function mountActions(modelValue: object[] = []) {
    return mount(OnCompleteActions as object, {
        props: { modelValue },
        global: { stubs: { ExportOnCompleteWizard: true, FileSourceNameSpan: true, GModal: true } },
    });
}

function lastActions(wrapper: ReturnType<typeof mountActions>) {
    return nth(wrapper.emitted<[object[]]>("update:modelValue"), -1)[0];
}

describe("OnCompleteActions", () => {
    beforeEach(() => {
        vi.mocked(useFileSources).mockReturnValue({ hasWritable: ref(true) } as unknown as ReturnType<
            typeof useFileSources
        >);
    });

    it("drops the export action when the export switch is turned off", async () => {
        const wrapper = mountActions([{ export_to_file_source: EXPORT_CONFIG }]);
        const exportSwitch = wrapper.find("[data-test-id='export-enabled-checkbox']");
        expect((exportSwitch.element as HTMLInputElement).checked).toBe(true);

        await exportSwitch.setValue(false);

        expect(lastActions(wrapper)).toEqual([]);
    });
});
