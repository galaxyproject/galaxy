import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import DatasetDetails from "./DatasetDetails.vue";

const PEEK = "<table><tr><td>col1</td></tr></table>";

vi.mock("@/api/datasets", async (importOriginal) => ({
    ...(await importOriginal<object>()),
    fetchDatasetDetails: vi.fn(async () => ({ id: "abc", creating_job: "job1", peek: PEEK })),
}));

vi.mock("@/composables/config", () => ({
    useConfig: () => ({ config: {}, isConfigLoaded: true }),
}));

const localVue = getLocalVue();
const { server, http } = useServerMock();

function mountDatasetDetails() {
    return shallowMount(DatasetDetails as object, {
        localVue,
        pinia: createTestingPinia({ createSpy: vi.fn }),
        propsData: { datasetId: "abc" },
    });
}

describe("DatasetDetails", () => {
    it("renders the dataset peek through v-sanitize-html", async () => {
        server.use(
            http.get("/api/jobs/{job_id}", ({ response }) => response(200).json({ id: "job1", state: "ok" } as never)),
        );
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const wrapper = mountDatasetDetails();
        await flushPromises();

        expect(sanitizeHtml).toHaveBeenCalledWith(PEEK, "default");
        expect(wrapper.find(".dataset-peek .sanitized td").text()).toBe("col1");
    });

    describe("creating job polling", () => {
        beforeEach(() => {
            vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
        });

        afterEach(() => {
            vi.useRealTimers();
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
                    wrapper.destroy();
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
