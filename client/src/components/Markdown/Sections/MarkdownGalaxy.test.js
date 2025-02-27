import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";
import { withPrefix } from "utils/redirect";

import MountTarget from "./MarkdownGalaxy.vue";

// mock routes
jest.mock("utils/redirect");
withPrefix.mockImplementation((url) => url);

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: {
            version_major: "test_version",
        },
        isConfigLoaded: true,
    })),
}));

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

describe("MarkdownContainer", () => {
    it("Renders version", async () => {
        const version = "test_version";
        const wrapper = await mountComponent({
            content: "generate_galaxy_version()",
        });
        const versionEl = wrapper.find(".galaxy-version");
        expect(versionEl.exists()).toBe(true);
        expect(versionEl.find("code").text()).toBe(version);

        // test collapsing
        const nolink = wrapper.find("a");
        expect(nolink.exists()).toBe(false);
        const collapse = "Click here to expand/collapse";
        await wrapper.setProps({ content: `generate_galaxy_version(collapse="${collapse}")` });
        const link = wrapper.find("a");
        expect(link.text()).toBe(collapse);
        const container = wrapper.find(".collapse");
        expect(container.attributes("style")).toBe("display: none;");
        await link.trigger("click");
        expect(container.attributes("style")).toBe("");
    });

    it("Renders time stamp", async () => {
        const time = new Date();
        jest.useFakeTimers().setSystemTime(time);
        const wrapper = await mountComponent({
            content: "generate_time()",
        });
        const version = wrapper.find(".galaxy-time");
        expect(version.exists()).toBe(true);
        expect(version.find("code").text()).toBe(time.toUTCString());
    });

    it("Renders history link", async () => {
        const wrapper = await mountComponent(
            {
                content: `history_link(history_id=test_history_id)`,
            },
            {
                onGet: { "/api/histories/test_history_id": { name: "history_name" } },
                onPost: { "/api/histories": {} },
            }
        );
        await flushPromises();
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
        const wrapper = await mountComponent(
            {
                content: `history_link(history_id=test_history_id)`,
            },
            {
                onGet: { "/api/histories/test_history_id": { name: "history_name" } },
            }
        );
        await wrapper.find("a").trigger("click");
        await flushPromises();
        const error = wrapper.find(".text-danger");
        const message = error.find("span");
        expect(message.text()).toBe("Failed to handle History: history_name!");
    });
});
