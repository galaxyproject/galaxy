import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { stopJobs } from "@/api/jobs";
import { jobsProvider } from "@/components/providers/JobProvider";

import JobsList from "./JobsList.vue";

vi.mock("@/components/providers/JobProvider", () => ({
    jobsProvider: vi.fn(async () => [
        { id: "job1", state: "running", user_id: "user1", update_time: "2026-10-06T11:29:52.707969" },
        { id: "job2", state: "queued", user_id: "user2", update_time: "2026-10-06T11:31:14.451511" },
    ]),
}));

vi.mock("@/api/jobs", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    stopJobs: vi.fn(async (jobIds: string[]) => ({ stopped: jobIds, failed: [] })),
}));

const localVue = getLocalVue();
const { server, http } = useServerMock();

async function mountJobsList() {
    const wrapper = mount(JobsList as object, {
        localVue,
        stubs: { JobLock: true, FilterMenu: true, UtcDate: true, JobDetails: true },
    });
    await flushPromises();
    return wrapper;
}

function headerBox(wrapper: Awaited<ReturnType<typeof mountJobsList>>) {
    return wrapper.find(".jobs-table thead input[type='checkbox']");
}

function rowBoxes(wrapper: Awaited<ReturnType<typeof mountJobsList>>) {
    return wrapper.findAll(".jobs-table tbody input[type='checkbox']").wrappers;
}

function isChecked(box: { element: Element }) {
    return (box.element as HTMLInputElement).checked;
}

describe("JobsList", () => {
    beforeEach(() => {
        vi.mocked(stopJobs).mockClear();
    });

    it("selects every unfinished job from the header checkbox", async () => {
        const wrapper = await mountJobsList();
        expect(rowBoxes(wrapper)).toHaveLength(2);

        await headerBox(wrapper).setChecked(true);
        await flushPromises();

        expect(rowBoxes(wrapper).map(isChecked)).toEqual([true, true]);
        expect(isChecked(headerBox(wrapper))).toBe(true);
        expect(wrapper.find("#stop-message").exists()).toBe(true);
    });

    it("stops every selected job on submit", async () => {
        const wrapper = await mountJobsList();
        await headerBox(wrapper).setChecked(true);
        await flushPromises();

        expect(wrapper.find("#stop-message").exists()).toBe(true);
        await wrapper.find("#stop-message").setValue("maintenance");
        const stopForm = wrapper.findAll("form").wrappers.find((form) => form.find("#stop-message").exists());
        await stopForm?.trigger("submit");
        await flushPromises();

        expect(stopJobs).toHaveBeenCalledTimes(1);
        expect(vi.mocked(stopJobs).mock.calls[0]?.slice(0, 2)).toEqual([["job1", "job2"], "maintenance"]);
        expect(wrapper.find(".alert-success").text()).toContain("Stopped 2 of 2 jobs.");
    });

    it("disables Submit and selection while a stop is in flight", async () => {
        let finish: (result: Awaited<ReturnType<typeof stopJobs>>) => void = () => {};
        vi.mocked(stopJobs).mockReturnValueOnce(new Promise((resolve) => (finish = resolve)));
        const wrapper = await mountJobsList();
        await headerBox(wrapper).setChecked(true);
        await flushPromises();

        await wrapper.find("#stop-message").setValue("maintenance");
        const stopForm = wrapper.findAll("form").wrappers.find((form) => form.find("#stop-message").exists());
        await stopForm?.trigger("submit");
        await flushPromises();

        expect(stopForm?.find("button[type='submit']").attributes("disabled")).toBeDefined();
        expect([headerBox(wrapper), ...rowBoxes(wrapper)].map((box) => box.attributes("disabled"))).toEqual([
            "disabled",
            "disabled",
            "disabled",
        ]);

        finish({ stopped: ["job1"], failed: [{ jobId: "job2", error: new Error("Too Many Requests") }] });
        await flushPromises();

        expect(stopForm?.find("button[type='submit']").attributes("disabled")).toBeUndefined();
        expect(rowBoxes(wrapper).map((box) => box.attributes("disabled"))).toEqual([undefined, undefined]);
    });

    it("checks the header once every row is ticked", async () => {
        const wrapper = await mountJobsList();
        for (const box of rowBoxes(wrapper)) {
            await box.setChecked(true);
        }
        await flushPromises();

        expect(isChecked(headerBox(wrapper))).toBe(true);
    });

    it("drops selected jobs that a refresh no longer lists", async () => {
        const wrapper = await mountJobsList();
        await headerBox(wrapper).setChecked(true);
        await flushPromises();

        const job3 = { id: "job3", state: "new", user_id: "user3", update_time: "2026-10-06T11:28:00.000000" };
        vi.mocked(jobsProvider).mockResolvedValueOnce([
            { id: "job1", state: "running", user_id: "user1", update_time: "2026-10-06T11:29:52.707969" },
            job3,
        ]);
        await wrapper.find('form[name="jobs"]').trigger("submit");
        await flushPromises();

        expect(rowBoxes(wrapper).map(isChecked)).toEqual([true, false]);
        expect(isChecked(headerBox(wrapper))).toBe(false);
        expect((headerBox(wrapper).element as HTMLInputElement).indeterminate).toBe(true);

        await wrapper.find("#stop-message").setValue("maintenance");
        const stopForm = wrapper.findAll("form").wrappers.find((form) => form.find("#stop-message").exists());
        await stopForm?.trigger("submit");
        await flushPromises();

        expect(stopJobs).toHaveBeenCalledTimes(1);
        expect(vi.mocked(stopJobs).mock.calls[0]?.slice(0, 2)).toEqual([["job1"], "maintenance"]);
    });

    it("reports jobs that could not be stopped and keeps them selected", async () => {
        vi.mocked(stopJobs).mockResolvedValueOnce({
            stopped: ["job1"],
            failed: [{ jobId: "job2", error: new Error("Too Many Requests") }],
        });
        const wrapper = await mountJobsList();
        await headerBox(wrapper).setChecked(true);
        await flushPromises();

        await wrapper.find("#stop-message").setValue("maintenance");
        const stopForm = wrapper.findAll("form").wrappers.find((form) => form.find("#stop-message").exists());
        await stopForm?.trigger("submit");
        await flushPromises();

        const alert = wrapper.find(".alert-danger");
        expect(alert.text()).toContain("Stopped 1 of 2 jobs.");
        expect(alert.text()).toContain("1 could not be stopped and remain selected: Too Many Requests");
        // Rows list the most recently updated job (job2) first.
        expect(rowBoxes(wrapper).map(isChecked)).toEqual([true, false]);
        expect((wrapper.find("#stop-message").element as HTMLInputElement).value).toBe("maintenance");
    });

    it("reports a failed refresh after stopping instead of hiding it", async () => {
        const wrapper = await mountJobsList();
        await headerBox(wrapper).setChecked(true);
        await flushPromises();

        vi.mocked(jobsProvider).mockRejectedValueOnce(new Error("Too Many Requests"));
        vi.spyOn(console, "log").mockImplementationOnce(() => {});
        await wrapper.find("#stop-message").setValue("maintenance");
        const stopForm = wrapper.findAll("form").wrappers.find((form) => form.find("#stop-message").exists());
        await stopForm?.trigger("submit");
        await flushPromises();

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
        const wrapper = await mountJobsList();
        await headerBox(wrapper).setChecked(true);
        await flushPromises();

        await wrapper.find("#send-notification").setChecked(true);
        await wrapper.find("#stop-message").setValue("maintenance");
        const stopForm = wrapper.findAll("form").wrappers.find((form) => form.find("#stop-message").exists());
        await stopForm?.trigger("submit");
        await flushPromises();

        expect(wrapper.find(".alert-warning").text()).toBe(
            "Stopped 2 of 2 jobs. Notification sent to 1 out of 2 users. 1 errors occurred.",
        );
    });

    it("warns when notifications cannot be sent at all", async () => {
        server.use(http.post("/api/notifications", ({ response }) => response.untyped(HttpResponse.error())));
        const wrapper = await mountJobsList();
        await headerBox(wrapper).setChecked(true);
        await flushPromises();

        await wrapper.find("#send-notification").setChecked(true);
        await wrapper.find("#stop-message").setValue("maintenance");
        const stopForm = wrapper.findAll("form").wrappers.find((form) => form.find("#stop-message").exists());
        await stopForm?.trigger("submit");
        await flushPromises();

        expect(wrapper.find(".alert-warning").text()).toMatch(
            /^Stopped 2 of 2 jobs\. Notifications could not be sent: /,
        );
    });
});
