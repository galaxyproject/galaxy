import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount, RouterLinkStub, shallowMount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { HDADetailed } from "@/api";
import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import DatasetPopoverLink from "./DatasetPopoverLink.vue";
import GPopover from "@/components/BaseComponents/GPopover.vue";

const RETRY_BACKOFF_CAP_MS = 30_000;

const { server, http } = useServerMock();

const DATASET_ID = "dataset-id-1";
const POPOVER_STUB = { name: "GPopoverStub", template: "<div><slot /></div>" };
const HISTORY_ID = "history-id-1";
const DATASET = { id: DATASET_ID, history_id: HISTORY_ID, name: "my dataset", peek: "", state: "ok" };

enableAutoUnmount(afterEach);

// The stubbed details child only needs the cached dataset identity and name.
type CachedDatasetName = Pick<HDADetailed, "id" | "name">;

function mountPopover(storedDatasets: Record<string, CachedDatasetName> = {}) {
    const wrapper = shallowMount(DatasetPopoverLink, {
        props: { datasetId: "dataset_id" },
        global: {
            plugins: [createTestingPinia({ createSpy: vi.fn, initialState: { datasetStore: { storedDatasets } } })],
            stubs: { RouterLink: true },
        },
    });
    return wrapper.getComponent(GPopover);
}

describe("DatasetPopoverLink", () => {
    it("lets keyboard users reach the links in the dataset details", () => {
        expect(mountPopover().props("interactive")).toBe(true);
    });

    it("uses a generic details label until the dataset is cached", () => {
        expect(mountPopover().props("ariaLabel")).toBe("Dataset details");
    });

    it("names the details dialog with the cached dataset name", () => {
        const popover = mountPopover({ dataset_id: { id: "dataset_id", name: "reads.fastq" } });
        expect(popover.props("ariaLabel")).toBe("reads.fastq");
    });
});

describe("DatasetPopoverLink loading", () => {
    let datasetRequests: number;
    let historyRequests: number;
    let failNext: number;
    let wrapper: VueWrapper | undefined;

    beforeEach(() => {
        datasetRequests = 0;
        historyRequests = 0;
        failNext = 0;
        server.use(
            http.get("/api/datasets/{dataset_id}", ({ response }) => {
                datasetRequests++;
                if (failNext > 0) {
                    failNext--;
                    return response("5XX").json({ err_msg: "unavailable", err_code: 0 }, { status: 503 });
                }
                return response.untyped(HttpResponse.json(DATASET));
            }),
            http.get("/api/histories/{history_id}", ({ response }) => {
                historyRequests++;
                return response.untyped(HttpResponse.json({ id: HISTORY_ID, name: "my history" }));
            }),
        );
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    /** Mounts with a GPopover stub that always renders its content. */
    function mountWithServer() {
        const localVue = getLocalVue();
        wrapper = mount(DatasetPopoverLink as object, {
            props: { datasetId: DATASET_ID },
            global: { ...localVue, stubs: { ...localVue.stubs, RouterLink: RouterLinkStub, GPopover: POPOVER_STUB } },
        });
        return wrapper;
    }

    it("does not fetch the dataset before hover", async () => {
        mountWithServer();
        await flushPromises();
        expect(datasetRequests).toBe(0);
        expect(historyRequests).toBe(0);
    });

    it("loads and displays dataset details on hover", async () => {
        const link = mountWithServer();
        await link.find(`#storage-run-item-dataset-${DATASET_ID}`).trigger("mouseenter");
        link.findComponent(POPOVER_STUB).vm.$emit("shown");
        await flushPromises();
        expect(datasetRequests).toBe(1);
        expect(link.find("#dataset-details").exists()).toBe(true);
        expect(link.find(".dataset-details-popover").text()).not.toContain("Loading dataset details");
    });

    it("shows loading during a retry backoff and the dataset once the retry succeeds", async () => {
        vi.useFakeTimers();
        failNext = 1;
        const link = mountWithServer();
        await link.find(`#storage-run-item-dataset-${DATASET_ID}`).trigger("mouseenter");
        link.findComponent(POPOVER_STUB).vm.$emit("shown");
        await flushPromises();
        expect(datasetRequests).toBe(1);
        expect(historyRequests).toBe(0);
        expect(link.find(".dataset-details-popover").text()).toContain("Loading dataset details");

        await vi.advanceTimersByTimeAsync(RETRY_BACKOFF_CAP_MS);
        await flushPromises();
        expect(datasetRequests).toBe(2);
        expect(link.find(".dataset-details-popover").text()).not.toContain("Loading dataset details");
        expect(link.find("#dataset-details").exists()).toBe(true);
        // Nothing in the popover reads the dataset's history.
        expect(historyRequests).toBe(0);
    });

    it("does not retry a failed fetch after the popover is hidden", async () => {
        vi.useFakeTimers();
        failNext = 1;
        const link = mountWithServer();
        await link.find(`#storage-run-item-dataset-${DATASET_ID}`).trigger("mouseenter");
        const popover = link.findComponent(POPOVER_STUB);
        popover.vm.$emit("shown");
        await flushPromises();
        expect(datasetRequests).toBe(1);

        popover.vm.$emit("hidden");
        await vi.advanceTimersByTimeAsync(RETRY_BACKOFF_CAP_MS);
        await flushPromises();
        expect(datasetRequests).toBe(1);
    });
});
