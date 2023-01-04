import axios from "axios";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MockAdapter from "axios-mock-adapter";
import TargetComponent from "./MarkdownContainer.vue";

const localVue = getLocalVue();

async function mountComponent(propsData, apiMap = {}) {
    const axiosMock = new MockAdapter(axios);
    for (const [path, response] of Object.entries(apiMap)) {
        axiosMock.onGet(path).reply(200, response);
    }
    return mount(TargetComponent, {
        localVue,
        propsData,
    });
}

async function testCollapse(wrapper) {
    const nolink = wrapper.find("a");
    expect(nolink.exists()).toBe(false);
    const collapse = "Click here to expand/collapse";
    await wrapper.setProps({
        args: {
            collapse,
        },
    });
    const link = wrapper.find("a");
    expect(link.text()).toBe(collapse);
    const container = wrapper.find(".collapse");
    expect(container.attributes("style")).toBe("display: none;");
    await link.trigger("click");
    expect(container.attributes("style")).toBe("");
}

describe("MarkdownContainer", () => {
    it("Should render version", async () => {
        const version = "test_version";
        const wrapper = await mountComponent({
            name: "generate_galaxy_version",
            args: {},
            version,
        });
        const versionEl = wrapper.find(".galaxy-version");
        expect(versionEl.exists()).toBe(true);
        expect(versionEl.find("code").text()).toBe(version);
        testCollapse(wrapper);
    });

    it("Should render time stamp", async () => {
        const time = "test_time";
        const wrapper = await mountComponent({
            name: "generate_time",
            args: {},
            time,
        });
        const version = wrapper.find(".galaxy-time");
        expect(version.exists()).toBe(true);
        expect(version.find("code").text()).toBe(time);
        testCollapse(wrapper);
    });
});
