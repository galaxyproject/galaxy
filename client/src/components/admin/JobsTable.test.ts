import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import JobsTable from "./JobsTable.vue";

const localVue = getLocalVue();

const fields = [
    { key: "id", label: "Job ID" },
    { key: "update_time", label: "Last Update", sortable: true },
];

// Oldest first, so the test fails unless the table sorts newest first itself
const items = [
    { id: "older", update_time: "2026-10-06T11:29:52.707969" },
    { id: "newer", update_time: "2026-10-06T11:31:14.451511" },
];

function mountJobsTable() {
    return mount(JobsTable as object, {
        propsData: { tableCaption: "Unfinished Jobs", fields, items, busy: false },
        localVue,
        stubs: { UtcDate: true, JobDetails: true },
    });
}

function renderedJobIds(wrapper: ReturnType<typeof mountJobsTable>) {
    return wrapper.findAll("tbody tr[id^='g-table-row-'] td:first-child").wrappers.map((td) => td.text());
}

describe("JobsTable", () => {
    it("shows the most recently updated jobs first", () => {
        const wrapper = mountJobsTable();
        expect(renderedJobIds(wrapper)).toEqual(["newer", "older"]);
    });

    it("toggles to oldest first when the Last Update header is clicked", async () => {
        const wrapper = mountJobsTable();
        await wrapper.findAll("thead th").at(1).trigger("click");
        expect(renderedJobIds(wrapper)).toEqual(["older", "newer"]);
    });
});
