import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import flushPromises from "flush-promises";
import MockAdapter from "axios-mock-adapter";

import axios from "axios";
import WorkflowExport from "./WorkflowExport";

const localVue = getLocalVue();
const axiosMock = new MockAdapter(axios);
axiosMock.onGet("/api/workflows/0").reply(200, {
    id: "0",
    name: "workflow",
});
axiosMock.onGet("/api/workflows/1").reply(200, {
    id: "1",
    owner: "owner",
    slug: "slug",
    importable: true,
});

function getHref(item) {
    return item.attributes("href");
}

describe("Workflow Export", () => {
    let wrapper;
    beforeEach(async () => {
        wrapper = shallowMount(
            WorkflowExport,
            {
                propsData: {
                    id: "0",
                },
            },
            localVue
        );
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
