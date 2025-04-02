import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { mount } from "@vue/test-utils";
import Vue from "vue";

import { useServerMock } from "@/api/client/__mocks__";

import MarkdownVitessce from "./MarkdownVitessce.vue";

jest.mock("@/onload", () => ({
    getAppRoot: () => "/",
}));

Vue.directive("localize", {});

const { server, http } = useServerMock();

describe("MarkdownVitessce.vue", () => {
    it("displays error on invalid JSON", async () => {
        const wrapper = mount(MarkdownVitessce, {
            propsData: {
                content: "{invalid",
            },
            pinia: createTestingPinia(),
        });
        expect(wrapper.text()).toContain("SyntaxError");
    });

    it("shows info alert when invocation is missing", async () => {
        const content = {
            datasets: [
                {
                    name: "DS1",
                    files: [
                        {
                            fileType: "obs",
                            __gx_dataset_label: {
                                input: "a",
                                invocation_id: null,
                            },
                        },
                    ],
                },
            ],
        };
        const wrapper = mount(MarkdownVitessce, {
            propsData: {
                content: JSON.stringify(content),
            },
        });
        expect(wrapper.text()).toContain("Data for rendering this Vitessce Dashboard is not yet available.");
    });

    it("uses dataset ID directly when __gx_dataset_id is present", async () => {
        const content = {
            datasets: [
                {
                    name: "DS1",
                    files: [
                        {
                            fileType: "obs",
                            __gx_dataset_id: "123",
                        },
                    ],
                },
            ],
        };
        const wrapper = mount(MarkdownVitessce, {
            propsData: {
                content: JSON.stringify(content),
            },
        });
        const config = wrapper.vm.visualizationConfig;
        expect(config.dataset_content.datasets[0].files[0].url).toBe("/api/datasets/123/display");
        expect(config.dataset_content.datasets[0].files[0].__gx_dataset_id).toBeUndefined();
    });

    it("resolves __gx_dataset_label via invocation and uses dataset URL", async () => {
        server.use(
            http.get("/api/invocations/{invocation_id}", ({ response }) =>
                response(200).json({
                    inputs: [
                        {
                            label: "some_input",
                            id: "label_id",
                        },
                    ],
                })
            )
        );
        const content = {
            datasets: [
                {
                    name: "DS1",
                    files: [
                        {
                            fileType: "obs",
                            __gx_dataset_label: {
                                input: "some_input",
                                invocation_id: "inv123",
                            },
                        },
                    ],
                },
            ],
        };
        const localVue = getLocalVue(true);
        localVue.component("VisualizationWrapper", {
            template: "<div class='viz-wrapper-stub' />",
        });
        const pinia = createTestingPinia({ stubActions: false });
        const wrapper = mount(MarkdownVitessce, {
            propsData: {
                content: JSON.stringify(content),
            },
            localVue,
            pinia,
        });
        await new Promise((resolve) => setTimeout(resolve));
        const file = wrapper.vm.visualizationConfig.dataset_content.datasets[0].files[0];
        expect(file.url).toBe("/api/datasets/label_id/display");
        expect(file.__gx_dataset_label).toBeUndefined();
    });
});
