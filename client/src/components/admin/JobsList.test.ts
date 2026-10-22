import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { deleteJob } from "@/api/jobs";
import { jobsProvider } from "@/components/providers/JobProvider";

import JobsList from "./JobsList.vue";

vi.mock("@/api/jobs", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    deleteJob: vi.fn(),
}));

vi.mock("@/components/providers/JobProvider", () => ({
    jobsProvider: vi.fn(),
}));

const globalConfig = getLocalVue();

const JOBS = [
    { id: "job1", state: "running", tool_id: "cat1", update_time: "2026-01-01T00:00:00" },
    { id: "job2", state: "queued", tool_id: "cat2", update_time: "2026-01-01T00:00:00" },
];

async function mountJobsList(attachTo?: HTMLElement, jobs: object[] = JOBS) {
    vi.mocked(jobsProvider).mockResolvedValue(jobs);
    vi.mocked(deleteJob).mockResolvedValue(true);
    const wrapper = mount(JobsList as object, {
        attachTo,
        global: {
            ...globalConfig,
            stubs: {
                ...globalConfig.stubs,
                FilterMenu: true,
                FontAwesomeIcon: true,
                JobDetails: true,
                JobLock: true,
                UtcDate: true,
            },
        },
    });
    await flushPromises();
    return wrapper;
}

type JobsListWrapper = Awaited<ReturnType<typeof mountJobsList>>;

function headerBox(wrapper: JobsListWrapper) {
    return wrapper.find('.jobs-table thead input[type="checkbox"]');
}

function rowBoxes(wrapper: JobsListWrapper) {
    return wrapper.findAll('.jobs-table tbody input[type="checkbox"]');
}

async function stopSelected(wrapper: JobsListWrapper, message: string) {
    await wrapper.find("#stop-message").setValue(message);
    await wrapper.find("#stop-message").element.closest("form")!.dispatchEvent(new Event("submit"));
    await flushPromises();
}

describe("JobsList", () => {
    it("stops only the jobs ticked in the unfinished jobs table", async () => {
        const wrapper = await mountJobsList();
        const rows = rowBoxes(wrapper);
        expect(rows.map((row) => row.attributes("aria-label"))).toEqual(["Select job job1", "Select job job2"]);
        expect(wrapper.find("#stop-message").exists()).toBe(false);

        await rows[0]!.setValue(true);
        expect(wrapper.find("#stop-message").exists()).toBe(true);
        await rows[0]!.setValue(false);
        expect(wrapper.find("#stop-message").exists()).toBe(false);

        await rows[1]!.setValue(true);
        expect((rows[1]!.element as HTMLInputElement).checked).toBe(true);
        expect(headerBox(wrapper).element).toHaveProperty("indeterminate", true);

        await stopSelected(wrapper, "maintenance");

        expect(deleteJob).toHaveBeenCalledTimes(1);
        expect(deleteJob).toHaveBeenCalledWith("job2", "maintenance");
    });

    it("selects and stops every unfinished job through the select-all box", async () => {
        const wrapper = await mountJobsList();
        vi.mocked(deleteJob).mockClear();
        const selectAll = headerBox(wrapper);
        const rows = rowBoxes(wrapper);
        expect(selectAll.attributes("aria-label")).toBe("Select all jobs");

        await selectAll.setValue(true);
        expect(rows.map((row) => (row.element as HTMLInputElement).checked)).toEqual([true, true]);
        expect(selectAll.element).toHaveProperty("checked", true);
        expect(selectAll.element).toHaveProperty("indeterminate", false);

        await stopSelected(wrapper, "maintenance");
        expect(deleteJob).toHaveBeenCalledTimes(2);
        expect(deleteJob).toHaveBeenCalledWith("job1", "maintenance");
        expect(deleteJob).toHaveBeenCalledWith("job2", "maintenance");
    });

    it("clears every job through the select-all box", async () => {
        const wrapper = await mountJobsList();
        const selectAll = headerBox(wrapper);
        const rows = rowBoxes(wrapper);

        await selectAll.setValue(true);
        expect(rows.map((row) => (row.element as HTMLInputElement).checked)).toEqual([true, true]);

        await selectAll.setValue(false);
        expect(rows.map((row) => (row.element as HTMLInputElement).checked)).toEqual([false, false]);
        expect(selectAll.element).toHaveProperty("checked", false);
        expect(wrapper.find("#stop-message").exists()).toBe(false);
    });

    it("drops selected jobs that a refresh no longer lists", async () => {
        const wrapper = await mountJobsList();
        vi.mocked(deleteJob).mockClear();
        await headerBox(wrapper).setValue(true);

        vi.mocked(jobsProvider).mockResolvedValueOnce([JOBS[0]]);
        await wrapper.find('form[name="jobs"]').trigger("submit");
        await flushPromises();

        const rows = rowBoxes(wrapper);
        expect(rows.map((row) => (row.element as HTMLInputElement).checked)).toEqual([true]);
        const selectAll = headerBox(wrapper);
        expect(selectAll.element).toHaveProperty("checked", true);
        expect(selectAll.element).toHaveProperty("indeterminate", false);

        await stopSelected(wrapper, "maintenance");
        expect(deleteJob).toHaveBeenCalledTimes(1);
        expect(deleteJob).toHaveBeenCalledWith("job1", "maintenance");
    });

    it("marks the select-all box as partial when a refresh adds jobs", async () => {
        const wrapper = await mountJobsList();
        await headerBox(wrapper).setValue(true);

        const newJob = { id: "job3", state: "new", tool_id: "cat3", update_time: "2026-01-01T00:00:00" };
        vi.mocked(jobsProvider).mockResolvedValueOnce([...JOBS, newJob]);
        await wrapper.find('form[name="jobs"]').trigger("submit");
        await flushPromises();

        const rows = rowBoxes(wrapper);
        expect(rows).toHaveLength(3);
        const selectAll = headerBox(wrapper);
        expect(selectAll.element).toHaveProperty("checked", false);
        expect(selectAll.element).toHaveProperty("indeterminate", true);
    });

    it("reloads every unfinished job when the time cutoff is switched off", async () => {
        const wrapper = await mountJobsList();
        await wrapper.find("#show-all-running").setValue(true);
        await flushPromises();

        expect(vi.mocked(jobsProvider).mock.lastCall![0]).toHaveProperty("state");
        expect(wrapper.text()).toContain("Showing all unfinished jobs");
    });

    it("ticks a job without opening its details", async () => {
        // Attached, so the click runs the checkbox activation and fires change
        const wrapper = await mountJobsList(document.body);
        await rowBoxes(wrapper)[0]!.trigger("click");

        expect(wrapper.find("#stop-message").exists()).toBe(true);
        expect(wrapper.find(".g-table-details-row").exists()).toBe(false);
        wrapper.unmount();
    });

    it("keeps the select-all box unticked while no job is unfinished", async () => {
        const finished = { id: "job3", state: "ok", tool_id: "cat3", update_time: "2026-01-01T00:00:00" };
        const wrapper = await mountJobsList(document.body, [finished]);
        const selectAll = headerBox(wrapper);

        await selectAll.trigger("click");
        expect(selectAll.element).toHaveProperty("checked", false);
        expect(selectAll.attributes("disabled")).toBeDefined();
        wrapper.unmount();
    });
});
