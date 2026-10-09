import { getFakeWorkflowSummary } from "@tests/test-data/workflows";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import WorkflowExport from "./WorkflowExport.vue";

enableAutoUnmount(afterEach);
const { server, http } = useServerMock();

function registerWorkflow(workflow) {
    server.use(
        http.get("/api/workflows/{workflow_id}", ({ params, response }) => {
            expect(params.workflow_id).toBe(workflow.id);
            return response.untyped(HttpResponse.json(workflow));
        }),
    );
}

async function mountExport(id) {
    const wrapper = shallowMount(WorkflowExport, {
        props: { id },
        global: getLocalVue(),
    });
    await flushPromises();
    return wrapper;
}

function exportLinks(wrapper) {
    return wrapper.findAll("a").map((link) => link.attributes("href"));
}

describe("WorkflowExport", () => {
    it("offers download and image links for a private workflow", async () => {
        registerWorkflow(getFakeWorkflowSummary({ id: "0", name: "workflow" }));
        const wrapper = await mountExport("0");

        expect(exportLinks(wrapper)).toEqual([
            "/api/workflows/0/download?format=json-download",
            "/workflow/gen_image?id=0",
        ]);
    });

    it("reloads export links when the workflow id changes to an importable workflow", async () => {
        registerWorkflow(getFakeWorkflowSummary({ id: "0", name: "workflow" }));
        const wrapper = await mountExport("0");
        expect(exportLinks(wrapper)).toEqual([
            "/api/workflows/0/download?format=json-download",
            "/workflow/gen_image?id=0",
        ]);
        registerWorkflow(getFakeWorkflowSummary({ id: "1", owner: "owner", slug: "slug", importable: true }));

        await wrapper.setProps({ id: "1" });
        await flushPromises();

        expect(exportLinks(wrapper)).toEqual([
            "http://localhost/u/owner/w/slug/json",
            "/api/workflows/1/download?format=json-download",
            "/workflow/gen_image?id=1",
        ]);
    });
});
