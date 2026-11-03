import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import type { ExportRecord } from "@/components/Common/models/exportRecordModel";

import ExportRecordDetails from "./ExportRecordDetails.vue";

const localVue = getLocalVue();

const FAILED_RECORD = {
    id: "record-id",
    isReady: false,
    isPreparing: false,
    isUpToDate: false,
    hasFailed: true,
    date: new Date(),
    elapsedTime: "a minute ago",
    taskUUID: "task-uuid",
    canReimport: false,
    isStsDownload: false,
    canDownload: false,
    modelStoreFormat: "tgz",
    canExpire: false,
    isPermanent: true,
    hasExpired: false,
    errorMessage: "The export ran out of disk space.",
} as ExportRecord;

describe("ExportRecordDetails.vue", () => {
    it("shows the error message of a failed record", () => {
        const wrapper = mount(ExportRecordDetails as object, {
            global: localVue,
            props: { record: FAILED_RECORD, objectType: "history" },
        });

        const alert = wrapper.find(".alert-danger");
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("The export ran out of disk space.");
    });
});
