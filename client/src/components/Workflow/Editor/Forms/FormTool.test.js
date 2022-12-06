import { mount } from "@vue/test-utils";
import { getLocalVue, mockModule } from "tests/jest/helpers"
import FormTool from "./FormTool";
import MockCurrentUser from "components/providers/MockCurrentUser";
import MockConfigProvider from "components/providers/MockConfigProvider";
import Vuex from "vuex";
import { userStore } from "store/userStore";
import { configStore } from "store/configStore";

const localVue = getLocalVue();

describe("FormTool", () => {
    let wrapper;

    beforeEach(() => {
        const store = new Vuex.Store({
            modules: {
                user: mockModule(userStore),
                config: mockModule(configStore),
            },
        });

        wrapper = mount(FormTool, {
            propsData: {
                id: "input",
                datatypes: [],
                configForm: {
                    id: "tool_id+1.0",
                    name: "tool_name",
                    version: "1.0",
                    description: "description",
                    inputs: [],
                    help: "help_text",
                    versions: ["1.0", "2.0", "3.0"],
                    hasCitations: false,
                },
                nodeId: "id",
                nodeAnnotation: "",
                nodeLabel: "",
                nodeInputs: [],
                nodeOutputs: [],
                nodeActiveOutputs: {},
                postJobActions: {},
                getManager: () => {
                    return {};
                },
            },
            localVue,
            stubs: {
                CurrentUser: MockCurrentUser({ id: "fakeuser" }),
                ConfigProvider: MockConfigProvider({ id: "fakeconfig" }),
                FormElement: { template: "<div>form-element</div>" },
                ToolFooter: { template: "<div>tool-footer</div>" },
            },
            provide: { store },
        });
    });

    it("changes between different versions", async () => {
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
