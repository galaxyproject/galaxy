import { nth } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { setMockConfig } from "@/composables/__mocks__/config";
import { useFileSources } from "@/composables/fileSources";

import OnCompleteActions from "./OnCompleteActions.vue";

vi.mock("@/composables/config");
vi.mock("@/composables/fileSources");

const EXPORT_CONFIG = {
    target_uri: "gxfiles://export/results",
    model_store_format: "rocrate.zip",
    include_files: true,
    include_hidden: false,
    include_deleted: false,
};

function mountActions(value: object[] = []) {
    return mount(OnCompleteActions as object, {
        props: { value },
        global: { stubs: { ExportOnCompleteWizard: true, FileSourceNameSpan: true, GModal: true } },
    });
}

function lastActions(wrapper: ReturnType<typeof mountActions>) {
    return nth(wrapper.emitted<[object[]]>("input"), -1)[0];
}

describe("OnCompleteActions", () => {
    beforeEach(() => {
        setMockConfig({ enable_notification_system: true });
        vi.mocked(useFileSources).mockReturnValue({ hasWritable: ref(true) } as unknown as ReturnType<
            typeof useFileSources
        >);
    });

    it("toggles the notification action with the notification switch", async () => {
        const wrapper = mountActions();
        const notificationSwitch = wrapper.find("[data-test-id='send-notification-checkbox']");

        await notificationSwitch.setValue(true);
        expect(lastActions(wrapper)).toEqual([{ send_notification: {} }]);

        await notificationSwitch.setValue(false);
        expect(lastActions(wrapper)).toEqual([]);
    });

    it("drops the export action when the export switch is turned off", async () => {
        const wrapper = mountActions([{ export_to_file_source: EXPORT_CONFIG }]);
        const exportSwitch = wrapper.find("[data-test-id='export-enabled-checkbox']");
        expect((exportSwitch.element as HTMLInputElement).checked).toBe(true);

        await exportSwitch.setValue(false);

        expect(lastActions(wrapper)).toEqual([]);
    });
});
