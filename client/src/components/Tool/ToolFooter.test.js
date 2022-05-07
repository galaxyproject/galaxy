import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import flushPromises from "flush-promises";
import ToolFooter from "./ToolFooter";

const localVue = getLocalVue(true);

const citationsA = [{ format: "bibtex", content: "@misc{entry_a, year = {1111}}" }];
const citationsB = [{ format: "bibtex", content: "@misc{entry_b, year = {2222}}" }];

describe("ToolFooter", () => {
    let wrapper;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(`/api/tools/tool_a/citations`).reply(200, citationsA);
        axiosMock.onGet(`/api/tools/tool_b/citations`).reply(200, citationsB);

        wrapper = mount(ToolFooter, {
            propsData: {
                id: "tool_a",
                hasCitations: true,
                xrefs: [],
                license: "tool_license",
                creators: [],
                requirements: [],
            },
            localVue,
            stubs: {
                Citation: false,
                License: true,
                Creators: true,
                FontAwesomeIcon: true,
            },
        });
    });

    afterEach(() => {
        axiosMock.restore();
        axiosMock.reset();
    });

    it("check props", async () => {
        await flushPromises();
        expect(wrapper.findAll(".footer-section-name").at(0).text()).toBeLocalizationOf("Citations");
        const referenceA = wrapper.find(".formatted-reference .csl-entry");
        expect(referenceA.attributes()["data-csl-entry-id"]).toBe("entry_a");
        expect(referenceA.text()).toContain("1111");
        await wrapper.setProps({ id: "tool_b" });
        await flushPromises();
        const referenceB = wrapper.find(".formatted-reference .csl-entry");
        expect(referenceB.attributes()["data-csl-entry-id"]).toBe("entry_b");
        expect(referenceB.text()).toContain("2222");
    });
});
