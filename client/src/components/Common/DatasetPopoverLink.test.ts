import { getLocalVue } from "@tests/vitest/helpers";
import { mount, RouterLinkStub, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import DatasetPopoverLink from "./DatasetPopoverLink.vue";

const RETRY_BACKOFF_CAP_MS = 30_000;

const localVue = getLocalVue();
const { server, http } = useServerMock();

const DATASET_ID = "dataset-id-1";
const POPOVER_STUB = { name: "BPopoverStub", template: "<div><slot /></div>" };
const HISTORY_ID = "history-id-1";
const DATASET = { id: DATASET_ID, history_id: HISTORY_ID, name: "my dataset", peek: "", state: "ok" };

describe("DatasetPopoverLink", () => {
    let datasetRequests: number;
    let historyRequests: number;
    let failNext: number;
    let wrapper: Wrapper<Vue> | undefined;

    beforeEach(() => {
        setActivePinia(createPinia());
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
        wrapper?.destroy();
        vi.useRealTimers();
    });

    /** Mounts with a BPopover stub that always renders its content, like the real one does. */
    function mountLink() {
        wrapper = mount(DatasetPopoverLink as object, {
            propsData: { datasetId: DATASET_ID },
            localVue,
            stubs: { RouterLink: RouterLinkStub, BPopover: POPOVER_STUB },
        });
        return wrapper;
    }

    it("does not fetch the dataset before hover", async () => {
        mountLink();
        await flushPromises();
        expect(datasetRequests).toBe(0);
        expect(historyRequests).toBe(0);
    });

    it("loads and displays dataset details on hover", async () => {
        const link = mountLink();
        await link.find(`#storage-run-item-dataset-${DATASET_ID}`).trigger("mouseenter");
        link.findComponent(POPOVER_STUB).vm.$emit("show");
        await flushPromises();
        expect(datasetRequests).toBe(1);
        expect(link.find("#dataset-details").exists()).toBe(true);
        expect(link.find(".dataset-details-popover").text()).not.toContain("Loading dataset details");
    });

    it("shows loading during a retry backoff and the dataset once the retry succeeds", async () => {
        vi.useFakeTimers();
        failNext = 1;
        const link = mountLink();
        await link.find(`#storage-run-item-dataset-${DATASET_ID}`).trigger("mouseenter");
        link.findComponent(POPOVER_STUB).vm.$emit("show");
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
        const link = mountLink();
        await link.find(`#storage-run-item-dataset-${DATASET_ID}`).trigger("mouseenter");
        const popover = link.findComponent(POPOVER_STUB);
        popover.vm.$emit("show");
        await flushPromises();
        expect(datasetRequests).toBe(1);

        popover.vm.$emit("hidden");
        await vi.advanceTimersByTimeAsync(RETRY_BACKOFF_CAP_MS);
        await flushPromises();
        expect(datasetRequests).toBe(1);
    });
});
