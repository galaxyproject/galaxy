import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import WorkflowRunDefaultStep from "./WorkflowRunDefaultStep.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue();

function collectionInput(hdca) {
    return { name: "f1", type: "data_collection", options: { hdca } };
}

describe("WorkflowRunDefaultStep", () => {
    it("keeps both entries of a collection loaded on the same page", async () => {
        const listed = { id: "hdca1", hid: 1, name: "listed", src: "hdca" };
        const nested = { id: "hdca9", hid: 9, name: "nested", src: "hdca" };
        const nestedMapped = { ...nested, map_over_type: "list" };
        server.use(
            http.untyped.post("/api/tools/tool_id/build", () => {
                return HttpResponse.json({ inputs: [collectionInput([nested, nestedMapped])] });
            }),
        );
        const wrapper = shallowMount(WorkflowRunDefaultStep, {
            propsData: {
                model: {
                    id: "tool_id",
                    version: "1.0",
                    index: 0,
                    fixed_title: "step",
                    inputs: [collectionInput([listed])],
                },
                validationScrollTo: [],
                historyId: "history_id",
            },
            localVue,
            pinia: createTestingPinia({ createSpy: vi.fn }),
        });

        wrapper.vm.onLoadMore({ name: "f1", src: "hdca", offset: 1, limit: 2 });
        await flushPromises();

        expect(wrapper.vm.modelInputs[0].options.hdca).toEqual([listed, nested, nestedMapped]);
    });
});
