import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import WorkflowLicense from "./WorkflowLicense.vue";

const localVue = getLocalVue();

const { server, http } = useServerMock();

describe("Workflow License", () => {
    function mountTarget() {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        server.use(
            http.get("/api/workflows/{workflow_id}", ({ response }) =>
                response(200).json({
                    license: "MIT",
                }),
            ),
            http.get("/api/licenses/MIT", ({ response }) =>
                response(200).json({
                    licenseId: "MIT",
                    name: "MIT License",
                    url: "https://opensource.org/licenses/MIT",
                }),
            ),
        );
        return mount(WorkflowLicense, {
            localVue,
            pinia,
            propsData: { workflowId: "workflow_id" },
        });
    }

    it("should render name and link", async () => {
        const wrapper = mountTarget();
        expect(wrapper.find("[title='loading']").exists()).toBeTruthy();
        await flushPromises();
        expect(wrapper.text()).toBe("MIT License");
        expect(wrapper.find("[href='https://opensource.org/licenses/MIT']").exists()).toBeTruthy();
    });
});
