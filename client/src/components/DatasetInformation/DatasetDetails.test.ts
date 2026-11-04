import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { http as mswHttp } from "msw";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { sanitizeHtml } from "@/directives/sanitizeHtml";

import DatasetDetails from "./DatasetDetails.vue";

vi.mock("@/composables/config");

// Stubbed by module: as <script setup> imports they can't be stubbed by name, and the real ones fetch more.
function stubComponent(name: string, render?: (props: Record<string, any>) => string) {
    return {
        default: {
            name,
            props: ["dataset", "datasetId", "jobId", "datasetName", "dependencies"],
            render(this: { $props: Record<string, any> }, h: (tag: string, data: object, text?: string) => unknown) {
                return h("div", { class: name }, render?.(this.$props));
            },
        },
    };
}
vi.mock("@/components/DatasetInformation/DatasetInformation.vue", () =>
    stubComponent("DatasetInformation", (props) => `size ${props.dataset.file_size}`),
);
vi.mock("@/components/Dataset/DatasetStorage/DatasetStorage.vue", () => stubComponent("DatasetStorage"));
vi.mock("@/components/InheritanceChain//InheritanceChain.vue", () => stubComponent("InheritanceChain"));
vi.mock("@/components/JobDependencies/JobDependencies.vue", () => stubComponent("JobDependencies"));
vi.mock("@/components/JobDestinationParams/JobDestinationParams.vue", () => stubComponent("JobDestinationParams"));
vi.mock("@/components/JobInformation/JobInformation.vue", () => stubComponent("JobInformation"));
vi.mock("@/components/JobMetrics/JobMetrics.vue", () => stubComponent("JobMetrics"));
vi.mock("@/components/JobParameters/JobParameters.vue", () => stubComponent("JobParameters"));

const DATASET_ID = "dataset_id";
const PEEK = "<table><tr><td>col1</td></tr></table>";
const JOB_ID = "job_id";

const localVue = getLocalVue();
const { server, http } = useServerMock();

const dataset = {
    id: DATASET_ID,
    name: "Test Dataset",
    state: "ok",
    file_ext: "txt",
    file_size: 100,
    peek: "<pre>first peek</pre>",
    creating_job: JOB_ID,
    update_time: "2026-01-01T00:00:00",
};

function serveDataset(served: object) {
    server.use(
        http.untyped.get("/api/datasets/:dataset_id", () => {
            return HttpResponse.json(served);
        }),
        http.untyped.get("/api/jobs/:job_id", () => {
            return HttpResponse.json({ id: JOB_ID, state: "ok" });
        }),
    );
}

function mountDatasetDetailsNow() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    return mount(DatasetDetails as object, {
        propsData: { datasetId: DATASET_ID },
        localVue,
        pinia,
    });
}

async function mountDatasetDetails() {
    const wrapper = mountDatasetDetailsNow();
    await flushPromises();
    return wrapper;
}

describe("DatasetDetails", () => {
    it("shows the dataset, its job and its peek", async () => {
        serveDataset(dataset);
        const wrapper = await mountDatasetDetails();
        expect(wrapper.find(".DatasetInformation").text()).toBe("size 100");
        expect(wrapper.find(".JobInformation").exists()).toBe(true);
        expect(wrapper.find(".dataset-peek").text()).toBe("first peek");
        expect(wrapper.text()).not.toContain("Job Not Found");
    });

    it("explains a dataset without a creating job", async () => {
        serveDataset({ ...dataset, creating_job: null });
        const wrapper = await mountDatasetDetails();
        expect(wrapper.find(".DatasetInformation").text()).toBe("size 100");
        expect(wrapper.find(".JobInformation").exists()).toBe(false);
        expect(wrapper.text()).toContain("Job Not Found");
    });

    it("renders the dataset peek through v-sanitize-html", async () => {
        serveDataset({ ...dataset, peek: PEEK });
        vi.mocked(sanitizeHtml).mockImplementation((html) => `<span class="sanitized">${html}</span>`);
        const wrapper = await mountDatasetDetails();

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
            serveDataset(dataset);
            server.use(
                mswHttp.get("/api/jobs/:job_id", () => {
                    jobRequests += 1;
                    return jobRequests === 1 ? HttpResponse.error() : HttpResponse.json({ id: JOB_ID, state: "ok" });
                }),
            );

            await mountDatasetDetails();
            await vi.waitFor(() => expect(jobRequests).toBe(1));
            await flushPromises();

            await vi.advanceTimersByTimeAsync(3000);
            await vi.waitFor(() => expect(jobRequests).toBe(2));
        });

        it("stops polling when unmounted while a failed job request is in flight", async () => {
            let jobRequests = 0;
            serveDataset(dataset);
            server.use(
                mswHttp.get("/api/jobs/:job_id", () => {
                    jobRequests += 1;
                    wrapper.unmount();
                    return HttpResponse.error();
                }),
            );

            const wrapper = mountDatasetDetailsNow();
            await vi.waitFor(() => expect(jobRequests).toBe(1));
            await flushPromises();

            await vi.advanceTimersByTimeAsync(3000);
            await flushPromises();
            expect(jobRequests).toBe(1);
        });
    });
});
