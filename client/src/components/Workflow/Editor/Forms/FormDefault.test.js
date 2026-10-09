import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { h } from "vue";

import { createTestStep } from "@/components/Workflow/Editor/test_fixtures";
import { useRefreshFromStore } from "@/stores/refreshFromStore";

import FormCollectionType from "./FormCollectionType.vue";
import FormDefault from "./FormDefault.vue";
import FormInputCollection from "./FormInputCollection.vue";

vi.mock("./FormDatatype.vue", () => ({ default: { render: () => h("div") } }));

enableAutoUnmount(afterEach);

function mountFormDefault(step) {
    const localVue = getLocalVue();
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    const wrapper = mount(FormDefault, {
        props: { datatypes: [], step },
        global: { ...withPlugins(localVue, pinia), provide: { workflowId: "mock-workflow" } },
    });
    return { wrapper, refreshStore: useRefreshFromStore() };
}

describe("FormDefault", () => {
    it("re-seeds the collection input form from the step on refresh", async () => {
        const collectionStep = {
            ...createTestStep(0, { outputs: [] }),
            content_id: null,
            annotation: "annotation",
            label: "label",
            name: "name",
            type: "data_collection_input",
            config_form: { inputs: [] },
            tool_state: { collection_type: '"list"' },
        };
        const { wrapper: collectionWrapper, refreshStore } = mountFormDefault(collectionStep);
        const collectionTypeField = () =>
            collectionWrapper.findComponent(FormInputCollection).findComponent(FormCollectionType);

        collectionTypeField().vm.$emit("onChange", "paired");
        await collectionWrapper.vm.$nextTick();
        expect(collectionTypeField().props("value")).toBe("paired");
        expect(collectionWrapper.emitted("onSetData")).toHaveLength(1);

        refreshStore.refresh();
        await collectionWrapper.vm.$nextTick();
        expect(collectionTypeField().props("value")).toBe("list");
        expect(collectionWrapper.emitted("onSetData")).toHaveLength(1);

        collectionTypeField().vm.$emit("onChange", "list:paired");
        expect(collectionWrapper.emitted("onSetData")).toHaveLength(2);
        expect(collectionWrapper.emitted("onSetData")[1][1].inputs.collection_type).toBe("list:paired");
    });

    it("renders the subworkflow title, metadata fields, and both output labels", () => {
        const step = {
            ...createTestStep(0, {
                outputs: [
                    { name: "output-name", label: "output-label" },
                    { name: "other-name", label: "other-label" },
                ],
            }),
            content_id: "id",
            annotation: "annotation",
            label: "label",
            name: "name",
            type: "subworkflow",
            config_form: { inputs: [] },
        };
        const { wrapper } = mountFormDefault(step);
        expect(wrapper.find(".portlet-title-text").text()).toBe("name");
        expect(wrapper.findAll("input")).toHaveLength(4);
        expect(wrapper.findAll("#__label__output-name")).toHaveLength(1);
        expect(wrapper.findAll("#__label__other-name")).toHaveLength(1);
    });
});
