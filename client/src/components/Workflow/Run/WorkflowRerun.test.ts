import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";

import WorkflowRerun from "./WorkflowRerun.vue";
import WorkflowRun from "./WorkflowRun.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

describe("WorkflowRerun", () => {
    let wrapper: Wrapper<Vue> | undefined;

    afterEach(() => {
        wrapper?.destroy();
        wrapper = undefined;
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it("switches to the original history before rendering the run form", async () => {
        const pinia = createPinia();
        const historyStore = useHistoryStore(pinia);
        let finishSwitch!: () => void;
        const switchHistory = vi.spyOn(historyStore, "setCurrentHistory").mockImplementation(
            () =>
                new Promise<void>((resolve) => {
                    finishSwitch = () => {
                        historyStore.setHistory({ id: "history-id", name: "Original history" } as Parameters<
                            typeof historyStore.setHistory
                        >[0]);
                        historyStore.setCurrentHistoryId("history-id");
                        resolve();
                    };
                }),
        );
        const toast = vi.spyOn(Toast, "error");
        server.use(
            http.get("/api/invocations/{invocation_id}/request", ({ response }) =>
                response.untyped(
                    HttpResponse.json({
                        history_id: "history-id",
                        workflow_id: "workflow-id",
                        instance: true,
                        inputs: { "0": { id: "dataset-id", src: "hda" } },
                        use_cached_job: true,
                    }),
                ),
            ),
        );
        wrapper = shallowMount(WorkflowRerun as object, {
            propsData: { invocationId: "invocation-id" },
            localVue,
            pinia,
        });
        await flushPromises();
        expect(switchHistory).toHaveBeenCalledWith("history-id");
        expect(wrapper.findComponent(WorkflowRun).exists()).toBe(false);
        finishSwitch();
        await flushPromises();
        expect(wrapper.findComponent(WorkflowRun).props()).toMatchObject({
            workflowId: "workflow-id",
            instance: true,
            isRerun: true,
            preferSimpleForm: true,
            requestState: { "0": { id: "dataset-id", src: "hda" } },
            simpleFormUseJobCache: true,
        });
        expect(toast).not.toHaveBeenCalled();
    });

    it("shows an alert when rerun data is unavailable", async () => {
        server.use(
            http.get("/api/invocations/{invocation_id}/request", ({ response }) =>
                response("4XX").json({ err_msg: "Invocation not found", err_code: 0 }, { status: 404 }),
            ),
        );
        wrapper = shallowMount(WorkflowRerun as object, {
            propsData: { invocationId: "invocation-id" },
            localVue,
            pinia: createPinia(),
        });
        await flushPromises();
        expect(wrapper.findComponent(GAlert).text()).toContain("Invocation not found");
        expect(wrapper.findComponent(WorkflowRun).exists()).toBe(false);
    });

    it("warns when the history switch returns without selecting the original history", async () => {
        const pinia = createPinia();
        vi.spyOn(useHistoryStore(pinia), "setCurrentHistory").mockResolvedValue();
        const toast = vi.spyOn(Toast, "error");
        server.use(
            http.get("/api/invocations/{invocation_id}/request", ({ response }) =>
                response.untyped(
                    HttpResponse.json({ history_id: "history-id", workflow_id: "workflow-id", instance: true }),
                ),
            ),
        );
        wrapper = shallowMount(WorkflowRerun as object, {
            propsData: { invocationId: "invocation-id" },
            localVue,
            pinia,
        });
        await flushPromises();
        expect(toast).toHaveBeenCalledExactlyOnceWith(
            "Unable to switch to the history with the original workflow inputs.",
        );
        expect(wrapper.findComponent(WorkflowRun).exists()).toBe(true);
    });
});
