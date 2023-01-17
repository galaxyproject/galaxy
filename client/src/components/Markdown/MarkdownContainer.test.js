import axios from "axios";
import flushPromises from "flush-promises";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MockAdapter from "axios-mock-adapter";
import { withPrefix } from "utils/redirect";
import MountTarget from "./MarkdownContainer.vue";

// mock routes
jest.mock("utils/redirect");
withPrefix.mockImplementation((url) => url);

const localVue = getLocalVue();
const axiosMock = new MockAdapter(axios);

async function mountComponent(propsData, apiMap = {}) {
    axiosMock.reset();
    for (const [method, apiDetails] of Object.entries(apiMap)) {
        for (const [path, response] of Object.entries(apiDetails)) {
            axiosMock[method](path).reply(200, response);
        }
    }
    return mount(MountTarget, {
        localVue,
        propsData,
        stubs: {
            FontAwesomeIcon: true,
        },
    });
}

async function testCollapse(wrapper) {
    const nolink = wrapper.find("a");
    expect(nolink.exists()).toBe(false);
    const collapse = "Click here to expand/collapse";
    await wrapper.setProps({ args: { collapse } });
    const link = wrapper.find("a");
    expect(link.text()).toBe(collapse);
    const container = wrapper.find(".collapse");
    expect(container.attributes("style")).toBe("display: none;");
    await link.trigger("click");
    expect(container.attributes("style")).toBe("");
}

describe("MarkdownContainer", () => {
    it("Renders version", async () => {
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

    it("Renders time stamp", async () => {
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

    it("Renders history link", async () => {
        const wrapper = await mountComponent(
            {
                name: "history_link",
                args: { history_id: "test_history_id" },
                histories: { test_history_id: { name: "history_name" } },
            },
            {
                onPost: { "/api/histories": {} },
            }
        );
        const link = wrapper.find("a");
        expect(link.text()).toBe("Click to Import History: history_name.");
        await link.trigger("click");
        const postedData = JSON.parse(axiosMock.history.post[0].data);
        expect(postedData.history_id).toBe("test_history_id");
        await flushPromises();
        const error = wrapper.find(".text-success");
        const message = error.find("span");
        expect(message.text()).toBe("Successfully Imported History: history_name!");
    });

    it("Renders history link (with failing import error message)", async () => {
        const wrapper = await mountComponent({
            name: "history_link",
            args: { history_id: "test_history_id" },
            histories: { test_history_id: { name: "history_name" } },
        });
        await wrapper.find("a").trigger("click");
        await flushPromises();
        const error = wrapper.find(".text-danger");
        const message = error.find("span");
        expect(message.text()).toBe("Failed to Import History: history_name!");
    });
});
