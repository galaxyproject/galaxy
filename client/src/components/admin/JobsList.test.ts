import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { stopJobs } from "@/api/jobs";
import { jobsProvider } from "@/components/providers/JobProvider";

import JobsList from "./JobsList.vue";

vi.mock("@/api/jobs", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    stopJobs: vi.fn(),
}));

vi.mock("@/components/providers/JobProvider", () => ({
    jobsProvider: vi.fn(),
}));

const globalConfig = getLocalVue();
const { server, http } = useServerMock();

const JOBS = [
    { id: "job1", state: "running", tool_id: "cat1", update_time: "2026-01-01T00:00:00" },
    { id: "job2", state: "queued", tool_id: "cat2", update_time: "2026-01-01T00:00:00" },
];

const JOBS_WITH_USERS = JOBS.map((job, index) => ({ ...job, user_id: `user${index + 1}` }));

async function mountJobsList(attachTo?: HTMLElement, jobs: object[] = JOBS) {
    vi.mocked(jobsProvider).mockResolvedValue(jobs);
    vi.mocked(stopJobs).mockImplementation(async (jobIds: string[]) => ({ stopped: jobIds, failed: [] }));
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

function isChecked(box: { element: Element }) {
    return (box.element as HTMLInputElement).checked;
}

function isDisabled(box: { element: Element }) {
    return (box.element as HTMLInputElement).disabled;
}

function stopFormOf(wrapper: JobsListWrapper) {
    return wrapper.findAll("form").find((form) => form.find("#stop-message").exists());
}

function stopCall(index = 0) {
    return vi.mocked(stopJobs).mock.calls[index]?.slice(0, 2);
}

async function stopSelected(wrapper: JobsListWrapper, message: string) {
    await wrapper.find("#stop-message").setValue(message);
    await wrapper.find("#stop-message").element.closest("form")!.dispatchEvent(new Event("submit"));
    await flushPromises();
}

describe("JobsList", () => {
    beforeEach(() => {
        vi.mocked(stopJobs).mockClear();
    });

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

        expect(stopJobs).toHaveBeenCalledTimes(1);
        expect(stopCall()).toEqual([["job2"], "maintenance"]);
        expect(wrapper.find(".alert-success").text()).toBe("Stopped 1 of 1 job.");
    });

    it("selects and stops every unfinished job through the select-all box", async () => {
        const wrapper = await mountJobsList();
        const selectAll = headerBox(wrapper);
        const rows = rowBoxes(wrapper);
        expect(selectAll.attributes("aria-label")).toBe("Select all jobs");

        await selectAll.setValue(true);
        expect(rows.map((row) => (row.element as HTMLInputElement).checked)).toEqual([true, true]);
        expect(selectAll.element).toHaveProperty("checked", true);
        expect(selectAll.element).toHaveProperty("indeterminate", false);

        await stopSelected(wrapper, "maintenance");
        expect(stopJobs).toHaveBeenCalledTimes(1);
        expect(stopCall()).toEqual([["job1", "job2"], "maintenance"]);
        expect(wrapper.find(".alert-success").text()).toContain("Stopped 2 of 2 jobs.");
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
        expect(stopJobs).toHaveBeenCalledTimes(1);
        expect(stopCall()).toEqual([["job1"], "maintenance"]);
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

    it("disables Submit and selection while a stop is in flight", async () => {
        let finish: (result: Awaited<ReturnType<typeof stopJobs>>) => void = () => {};
        const wrapper = await mountJobsList();
        vi.mocked(stopJobs).mockReturnValueOnce(new Promise((resolve) => (finish = resolve)));
        await headerBox(wrapper).setValue(true);

        await stopSelected(wrapper, "maintenance");
        const submit = stopFormOf(wrapper)!.find("button[type='submit']");
        expect(submit.attributes("disabled")).toBeDefined();
        expect([headerBox(wrapper), ...rowBoxes(wrapper)].map(isDisabled)).toEqual([true, true, true]);

        finish({ stopped: ["job1"], failed: [{ jobId: "job2", error: new Error("Too Many Requests") }] });
        await flushPromises();

        expect(stopFormOf(wrapper)!.find("button[type='submit']").attributes("disabled")).toBeUndefined();
        expect(rowBoxes(wrapper).map(isDisabled)).toEqual([false, false]);
    });

    it("reports jobs that could not be stopped and keeps them selected", async () => {
        const wrapper = await mountJobsList();
        vi.mocked(stopJobs).mockResolvedValueOnce({
            stopped: ["job1"],
            failed: [{ jobId: "job2", error: new Error("Too Many Requests") }],
        });
        await headerBox(wrapper).setValue(true);

        await stopSelected(wrapper, "maintenance");

        const alert = wrapper.find(".alert-danger");
        expect(alert.text()).toContain("Stopped 1 of 2 jobs.");
        expect(alert.text()).toContain("1 could not be stopped and remain selected: Too Many Requests");
        expect(rowBoxes(wrapper).map(isChecked)).toEqual([false, true]);
        expect((wrapper.find("#stop-message").element as HTMLInputElement).value).toBe("maintenance");
    });

    it("reports a failed refresh after stopping instead of hiding it", async () => {
        const wrapper = await mountJobsList();
        await headerBox(wrapper).setValue(true);

        vi.mocked(jobsProvider).mockRejectedValueOnce(new Error("Too Many Requests"));
        vi.spyOn(console, "log").mockImplementationOnce(() => {});
        await stopSelected(wrapper, "maintenance");

        expect(wrapper.find(".alert-danger").text()).toBe(
            "Stopped 2 of 2 jobs. Refreshing the job list failed: Too Many Requests",
        );
    });

    it("warns when some notifications could not be sent", async () => {
        server.use(
            http.post("/api/notifications", async ({ request, response }) => {
                const body = (await request.json()) as { recipients: { user_ids: string[] } };
                if (body.recipients.user_ids[0] === "user1") {
                    return response.untyped(HttpResponse.json({ err_msg: "Server Error" }, { status: 500 }));
                }
                return response.untyped(HttpResponse.json({}));
            }),
        );
        const wrapper = await mountJobsList(undefined, JOBS_WITH_USERS);
        await headerBox(wrapper).setValue(true);

        await wrapper.find("#send-notification").setValue(true);
        await stopSelected(wrapper, "maintenance");

        expect(wrapper.find(".alert-warning").text()).toBe(
            "Stopped 2 of 2 jobs. Notification sent to 1 out of 2 users. 1 errors occurred.",
        );
    });

    it("warns when notifications cannot be sent at all", async () => {
        server.use(http.post("/api/notifications", ({ response }) => response.untyped(HttpResponse.error())));
        const wrapper = await mountJobsList(undefined, JOBS_WITH_USERS);
        await headerBox(wrapper).setValue(true);

        await wrapper.find("#send-notification").setValue(true);
        await stopSelected(wrapper, "maintenance");

        expect(wrapper.find(".alert-warning").text()).toMatch(
            /^Stopped 2 of 2 jobs\. Notifications could not be sent: /,
        );
    });
});
