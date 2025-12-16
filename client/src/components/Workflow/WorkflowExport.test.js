import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import WorkflowExport from "./WorkflowExport.vue";

const localVue = getLocalVue();
const { server, http } = useServerMock();

server.use(
    http.untyped.get("/api/workflows/0", () => {
        return HttpResponse.json({
            id: "0",
            name: "workflow",
        });
    }),
    http.untyped.get("/api/workflows/1", () => {
        return HttpResponse.json({
            id: "1",
            owner: "owner",
            slug: "slug",
            importable: true,
        });
    }),
);

function getHref(item) {
    return item.attributes("href");
}

describe("Workflow Export", () => {
    let wrapper;
    beforeEach(async () => {
        wrapper = shallowMount(WorkflowExport, {
            props: {
                id: "0",
            },
            global: localVue,
        });
        await flushPromises();
        await nextTick();
    });

    it("verify display", async () => {
        let links = wrapper.findAll("a");
        expect(getHref(links.at(0))).toBe("/api/workflows/0/download?format=json-download");
        expect(getHref(links.at(1))).toBe("/workflow/gen_image?id=0");
        await wrapper.setProps({ id: "1" });
        await flushPromises();
        links = wrapper.findAll("a");
        expect(getHref(links.at(0))).toBe("http://localhost/u/owner/w/slug/json");
        expect(getHref(links.at(1))).toBe("/api/workflows/1/download?format=json-download");
        expect(getHref(links.at(2))).toBe("/workflow/gen_image?id=1");
    });
});
