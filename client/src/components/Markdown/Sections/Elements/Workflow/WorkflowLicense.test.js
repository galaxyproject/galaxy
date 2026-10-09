import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";

import WorkflowLicense from "./WorkflowLicense.vue";

enableAutoUnmount(afterEach);
const { server, http } = useServerMock();

describe("WorkflowLicense", () => {
    it("replaces the loading indicator with the workflow license name and link", async () => {
        server.use(
            http.get("/api/workflows/{workflow_id}", ({ params, response }) => {
                expect(params.workflow_id).toBe("workflow_id");
                return response(200).json({ license: "MIT" });
            }),
            http.get("/api/licenses/{license_id}", ({ params, response }) => {
                expect(params.license_id).toBe("MIT");
                return response(200).json({
                    licenseId: "MIT",
                    name: "MIT License",
                    url: "https://opensource.org/licenses/MIT",
                });
            }),
        );
        const wrapper = mount(WorkflowLicense, {
            global: getLocalVue(),
            props: { workflowId: "workflow_id" },
        });

        expect(wrapper.find("[title='loading']").exists()).toBe(true);
        await flushPromises();

        expect(wrapper.text()).toBe("MIT License");
        expect(wrapper.get("a[href='https://opensource.org/licenses/MIT']").text()).toBe("MIT License");
        expect(wrapper.find("[title='loading']").exists()).toBe(false);
    });
});
