import { composeStory } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { disposePinia, getActivePinia } from "pinia";
import { beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import * as Stories from "./DatasetDetails.stories";

const PEEK = "<table><tr><td>col1</td></tr></table>";

vi.mock("@/api/datasets", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    fetchDatasetDetails: vi.fn(async () => ({ id: "abc", creating_job: "job1", peek: PEEK })),
}));

vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config: {}, isConfigLoaded: true }),
}));

const mountStory = useStoryMount();
const { server, http } = useServerMock();
const initialSanitizeImplementation = vi.mocked(sanitizeHtml).getMockImplementation();

function mountDatasetDetails() {
    // Preserve the original parent-only API mocks and polling request counts.
    const story = composeStory({ ...Stories.CompletedDataset, parameters: { msw: { handlers: [] } } }, Stories.default);
    const wrapper = mountStory(story, {
        props: { datasetId: "abc" },
        global: {
            stubs: {
                Heading: true,
                GAlert: true,
                DatasetStorage: true,
                DatasetInformation: true,
                InheritanceChain: true,
                JobDependencies: true,
                JobDestinationParams: true,
                JobInformation: true,
                JobMetrics: true,
                JobParameters: true,
                LoadingSpan: true,
            },
        },
        pinia: { stubActions: true },
    });
    const pinia = getActivePinia()!;
    onTestFinished(() => {
        wrapper.unmount();
        disposePinia(pinia);
    });
    return wrapper;
}

describe("DatasetDetails", () => {
    beforeEach(() => {
        // Registered before mount cleanup so the directive stays intact through unmount.
        onTestFinished(() => {
            const sanitizer = vi.mocked(sanitizeHtml);
            sanitizer.mockClear();
            if (initialSanitizeImplementation) {
                sanitizer.mockImplementation(initialSanitizeImplementation);
            }
        });
    });
    it("renders the dataset peek through v-sanitize-html", async () => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) =>
                // This peek-only case needs the same deliberately partial job response.
                response.untyped(HttpResponse.json({ id: "job1", state: "ok" })),
            ),
        );
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const wrapper = mountDatasetDetails();
        await flushPromises();

        expect(sanitizeHtml).toHaveBeenCalledWith(PEEK, "default");
        expect(wrapper.get(".dataset-peek .sanitized td").text()).toBe("col1");
    });

    describe("creating job polling", () => {
        beforeEach(() => {
            vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
            onTestFinished(() => {
                vi.clearAllTimers();
                vi.useRealTimers();
            });
        });

        it("keeps polling the creating job after a request fails to reach the server", async () => {
            let jobRequests = 0;
            server.use(
                mswHttp.get("/api/jobs/:job_id", () => {
                    jobRequests += 1;
                    return jobRequests === 1 ? HttpResponse.error() : HttpResponse.json({ id: "job1", state: "ok" });
                }),
            );

            mountDatasetDetails();
            await vi.waitFor(() => expect(jobRequests).toBe(1));
            await flushPromises();

            await vi.advanceTimersByTimeAsync(3000);
            await vi.waitFor(() => expect(jobRequests).toBe(2));
        });

        it("stops polling when unmounted while a failed job request is in flight", async () => {
            let jobRequests = 0;
            server.use(
                mswHttp.get("/api/jobs/:job_id", () => {
                    jobRequests += 1;
                    wrapper.unmount();
                    return HttpResponse.error();
                }),
            );

            const wrapper = mountDatasetDetails();
            await vi.waitFor(() => expect(jobRequests).toBe(1));
            await flushPromises();

            await vi.advanceTimersByTimeAsync(3000);
            await flushPromises();
            expect(jobRequests).toBe(1);
        });
    });
});
