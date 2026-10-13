import { composeStories } from "@storybook/vue3-vite";
import { deferred } from "@tests/vitest/deferred";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { waitOnJob } from "@/components/JobStates/wait";

import * as HistoryImportStories from "./HistoryImport.stories";

import HistoryImport from "./HistoryImport.vue";

const stories = composeStories(HistoryImportStories);
const mountStory = useStoryMount();

const TEST_JOB_ID = "job123789";
const TEST_SOURCE_URL = "http://galaxy.example/import";

vi.mock("@/components/JobStates/wait", () => ({
    waitOnJob: vi.fn(),
}));

const { server, http } = useServerMock();

describe("HistoryImport.vue", () => {
    let wrapper;

    afterEach(async () => {
        // Settle pending URL debounce callbacks while the component is still mounted.
        await vi.runAllTimersAsync();
    });

    beforeEach(async () => {
        onTestFinished(() => {
            vi.clearAllTimers();
            vi.useRealTimers();
            vi.mocked(waitOnJob).mockReset();
        });
        vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        const root = mountStory(stories.HistoryWithRepository);
        await vi.waitFor(() => {
            wrapper = root.getComponent(HistoryImport);
            if (wrapper.vm.initializing) {
                throw new Error("File sources have not loaded yet");
            }
        });
    });

    it("should render a form with submit disabled because inputs empty", async () => {
        expect(wrapper.find(".import-button").exists()).toBeTruthy();
        expect(wrapper.get(".import-button").attributes("aria-disabled")).toBeTruthy();
        expect(wrapper.vm.importReady).toBeFalsy();
    });

    it("should allow import when URL available", async () => {
        await wrapper.setData({
            sourceURL: TEST_SOURCE_URL,
        });
        expect(wrapper.vm.importReady).toBeTruthy();
    });

    it("should require an URI if that is the import type", async () => {
        // Preserve the original invalid import-type contract as a unit-only override.
        await wrapper.setData({
            sourceURL: TEST_SOURCE_URL,
            importType: "sourceRemoteFilesUri",
        });
        expect(wrapper.vm.importReady).toBeFalsy();
    });

    it("should post to create a new history and wait on job when submitted", async () => {
        await wrapper.setData({
            sourceURL: TEST_SOURCE_URL,
        });
        let formData;

        server.use(
            http.post("/api/histories", async ({ response, request }) => {
                formData = await request.formData();
                // Preserve the legacy response shape only in this unit contract. Galaxy returns `id`.
                return response(200).json({ job_id: TEST_JOB_ID });
            }),
        );

        const jobCompletion = deferred();
        vi.mocked(waitOnJob).mockReturnValue(jobCompletion.promise);
        try {
            wrapper.vm.submit();
            await flushPromises();
            expect(formData.get("archive_source")).toBe(TEST_SOURCE_URL);
            expect(wrapper.vm.waitingOnJob).toBeTruthy();

            // Complete the held job before observing its finished state.
            jobCompletion.resolve({ state: "ok" });
            await flushPromises();
            expect(wrapper.vm.waitingOnJob).toBeFalsy();
            expect(wrapper.vm.complete).toBeTruthy();
        } finally {
            jobCompletion.resolve({ state: "ok" });
            await flushPromises();
        }
    });

    it("warns about shared history imports", async () => {
        const input = wrapper.get("input[type=url]");
        await input.setValue("https://usegalaxy.org/u/some_user/h/exported_history");

        await vi.advanceTimersByTimeAsync(210);

        const alert = wrapper.get(".alert");
        expect(alert.classes()).toContain("alert-warning");
        expect(alert.text()).toContain(
            "It looks like you are trying to import a published history from another galaxy instance",
        );

        // Link to the GTN
        const link = alert.get("a");
        expect(link.text()).toContain("GTN");
    });
});
