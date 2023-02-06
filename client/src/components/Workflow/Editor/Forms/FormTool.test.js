import { mount } from "@vue/test-utils";
import { getLocalVue, mockModule } from "tests/jest/helpers";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import FormTool from "./FormTool";
import MockCurrentUser from "components/providers/MockCurrentUser";
import MockConfigProvider from "components/providers/MockConfigProvider";
import Vuex from "vuex";
import { userStore } from "store/userStore";
import { configStore } from "store/configStore";
import { createTestingPinia } from "@pinia/testing";

const localVue = getLocalVue();

describe("FormTool", () => {
    const axiosMock = new MockAdapter(axios);
    axiosMock.onGet(`/api/webhooks`).reply(200, []);

    function mountTarget() {
        const store = new Vuex.Store({
            modules: {
                user: mockModule(userStore),
                config: mockModule(configStore),
            },
        });

        return mount(FormTool, {
            propsData: {
                id: "input",
                datatypes: [],
                step: {
                    id: 0,
                    config_form: {
                        id: "tool_id+1.0",
                        name: "tool_name",
                        version: "1.0",
                        description: "description",
                        inputs: [{ name: "input", label: "input", type: "text", value: "value" }],
                        help: "help_text",
                        versions: ["1.0", "2.0", "3.0"],
                        citations: false,
                    },
                    outputs: [],
                    inputs: [],
                    post_job_actions: {},
                },
            },
            localVue,
            stubs: {
                CurrentUser: MockCurrentUser({ id: "fakeuser" }),
                ConfigProvider: MockConfigProvider({ id: "fakeconfig" }),
                ToolFooter: { template: "<div>tool-footer</div>" },
            },
            pinia: createTestingPinia(),
            provide: { store },
        });
    }

    it("changes between different versions", async () => {
        const wrapper = mountTarget();

        const dropdowns = wrapper.findAll(".tool-versions .dropdown-item");
        let version = dropdowns.at(1);
        expect(version.text()).toBe("Switch to 2.0");
        await version.trigger("click");

        let state = wrapper.emitted().onSetData[0][1];
        expect(state.tool_version).toEqual("2.0");
        expect(state.tool_id).toEqual("tool_id+2.0");

        version = dropdowns.at(0);
        expect(version.text()).toBe("Switch to 3.0");
        await version.trigger("click");

        state = wrapper.emitted().onSetData[1][1];
        expect(state.tool_version).toEqual("3.0");
        expect(state.tool_id).toEqual("tool_id+3.0");
    });
});
