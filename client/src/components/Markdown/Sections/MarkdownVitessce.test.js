import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import MarkdownVitessce from "./MarkdownVitessce.vue";
import VisualizationWrapper from "./VisualizationWrapper.vue";

vi.mock("@/onload", () => ({
    getAppRoot: () => "/",
}));

enableAutoUnmount(afterEach);

const { server, http } = useServerMock();

function mountContent(content) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    return mount(MarkdownVitessce, {
        props: { content: typeof content === "string" ? content : JSON.stringify(content) },
        global: {
            ...withPlugins(getLocalVue(), pinia),
            stubs: { VisualizationWrapper: true },
        },
    });
}

describe("MarkdownVitessce.vue", () => {
    it("displays error on invalid JSON", () => {
        const wrapper = mountContent("{invalid");
        expect(wrapper.text()).toContain("SyntaxError");
    });

    it("shows info alert when invocation is missing", () => {
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
        const wrapper = mountContent(content);
        expect(wrapper.text()).toContain("Data for rendering this Vitessce Dashboard is not yet available.");
    });

    it("uses dataset ID directly when __gx_dataset_id is present", () => {
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
        const wrapper = mountContent(content);
        const config = wrapper.getComponent(VisualizationWrapper).props("config");
        expect(config.dataset_content.datasets[0].files[0]).toEqual({
            fileType: "obs",
            url: "/api/datasets/123/display",
        });
    });

    it("resolves __gx_dataset_label via invocation and uses dataset URL", async () => {
        server.use(
            http.get("/api/invocations/{invocation_id}", ({ response }) => {
                return response(200).json({
                    inputs: [{ label: "some_input", id: "label_id" }],
                });
            }),
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
        const wrapper = mountContent(content);
        // Resolving the label starts an HTTP request from the content watcher.
        await vi.waitFor(() => {
            const config = wrapper.getComponent(VisualizationWrapper).props("config");
            expect(config.dataset_content.datasets[0].files[0]).toEqual({
                fileType: "obs",
                url: "/api/datasets/label_id/display",
            });
        });
    });
});
