import { composeStory } from "@storybook/vue3-vite";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, disposePinia, getActivePinia, type Pinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, onTestFinished, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import * as DatasetAttributesStories from "./DatasetAttributes.stories";

import DatasetAttributes from "./DatasetAttributes.vue";

const DATASET_ID = "dataset_id";

const localVue = getLocalVue();
const { server, http } = useServerMock();
const mountStory = useStoryMount();

enableAutoUnmount(afterEach);

function ownedMountPlugins(pinia: Pinia) {
    onTestFinished(() => {
        disposePinia(pinia);
        if (getActivePinia() === pinia) {
            setActivePinia(undefined);
        }
    });
    return withPlugins(localVue, pinia);
}

async function mountDatasetAttributes(conversionDisabled = false) {
    // Keep the original synthetic fields/messages only in this unit contract.
    const story = composeStory(
        {
            ...(conversionDisabled
                ? DatasetAttributesStories.TextWithoutConverters
                : DatasetAttributesStories.EditableBed),
            args: { datasetId: DATASET_ID },
            parameters: {
                msw: {
                    handlers: {
                        save: http.untyped.put("/dataset/set_edit", () =>
                            HttpResponse.json({ message: "success", status: "success" }),
                        ),
                        edit: http.untyped.get("/dataset/get_edit", ({ request }) => {
                            const url = new URL(request.url);
                            if (url.searchParams.get("dataset_id") === DATASET_ID) {
                                return HttpResponse.json({
                                    attribute_inputs: [{ name: "attribute_text", type: "text" }],
                                    conversion_inputs: [{ name: "conversion_text", type: "text" }],
                                    conversion_disable: conversionDisabled,
                                    datatype_inputs: [{ name: "datatype_text", type: "text" }],
                                    permission_inputs: [{ name: "permission_text", type: "text" }],
                                });
                            }
                            return HttpResponse.json({}, { status: 404 });
                        }),
                    },
                },
            },
        },
        DatasetAttributesStories.default,
    );
    const root = mountStory(story);
    await vi.waitFor(() => root.getComponent(DatasetAttributes));
    await flushPromises();
    return root.getComponent(DatasetAttributes);
}

async function buildWrapperWithError(error: string) {
    server.use(
        http.untyped.get("/dataset/get_edit", () => {
            return HttpResponse.json({}, { status: 400 });
        }),
    );
    const wrapper = mount(DatasetAttributes, {
        props: {
            datasetId: DATASET_ID,
        },
        // These original values are fallthrough attributes, not declared component props.
        attrs: {
            messageText: error,
            messageVariant: "danger",
        },
        global: {
            ...ownedMountPlugins(createPinia()),
            stubs: {
                ...localVue.stubs,
                FontAwesomeIcon: false,
                FormElement: false,
            },
        },
    });
    await flushPromises();
    return wrapper;
}

describe("DatasetAttributes", () => {
    it("renders all edit sections and shows a successful save", async () => {
        const wrapper = await mountDatasetAttributes();

        // 6 form buttons (GTabs nav uses <a> tags, not buttons)
        expect(wrapper.findAll("button").length).toBe(6);
        expect(wrapper.findAll("#attribute_text").length).toBe(1);
        expect(wrapper.findAll("#conversion_text").length).toBe(1);
        expect(wrapper.findAll("#datatype_text").length).toBe(1);
        expect(wrapper.findAll("#permission_text").length).toBe(1);
        expect(wrapper.findAll(".tab-pane").length).toBe(3);
        expect(wrapper.findAll(".ui-portlet-section").length).toBe(2);

        const saveButton = wrapper.get("#dataset-attributes-default-save");

        await saveButton.trigger("click");

        await flushPromises();

        expect(wrapper.get(".dataset-attributes-alert").text()).toBe("success");
    });

    it("shows why saving failed", async () => {
        const wrapper = await mountDatasetAttributes();
        server.use(
            http.untyped.put("/dataset/set_edit", () => {
                return HttpResponse.json({ err_msg: "This dataset is encrypted." }, { status: 400 });
            }),
        );

        await wrapper.get("#dataset-attributes-default-save").trigger("click");
        await flushPromises();

        expect(wrapper.get(".dataset-attributes-alert").text()).toBe("This dataset is encrypted.");
    });

    it("omits conversion controls when conversion is disabled", async () => {
        const wrapper = await mountDatasetAttributes(true);

        // 5 form buttons (GTabs nav uses <a> tags, not buttons)
        expect(wrapper.findAll("button").length).toBe(5);
        expect(wrapper.findAll("#attribute_text").length).toBe(1);
        expect(wrapper.findAll("#conversion_text").length).toBe(0);
        expect(wrapper.findAll("#datatype_text").length).toBe(1);
        expect(wrapper.findAll("#permission_text").length).toBe(1);
        expect(wrapper.findAll(".tab-pane").length).toBe(3);
        expect(wrapper.findAll(".ui-portlet-section").length).toBe(1);
    });

    it("doesn't render edit controls with error", async () => {
        const wrapper = await buildWrapperWithError("error");
        expect(wrapper.findAll("button").length).toBe(0);
        expect(wrapper.findAll("#attribute_text").length).toBe(0);
        expect(wrapper.findAll("#conversion_text").length).toBe(0);
        expect(wrapper.findAll("#datatype_text").length).toBe(0);
        expect(wrapper.findAll("#permission_text").length).toBe(0);
        expect(wrapper.findAll(".tab-pane").length).toBe(0);
        expect(wrapper.findAll(".ui-portlet-section").length).toBe(0);
    });
});
