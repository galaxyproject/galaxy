import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import FormTool from "./FormTool";
import MockCurrentUser from "components/providers/MockCurrentUser";
import MockConfigProvider from "components/providers/MockConfigProvider";

const localVue = getLocalVue();

describe("FormTool", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(FormTool, {
            propsData: {
                id: "input",
                datatypes: [],
                getNode: () => {
                    return {
                        id: "id",
                        config_form: {
                            id: "tool_id+1.0",
                            name: "tool_name",
                            version: "1.0",
                            description: "description",
                            inputs: [],
                            help: "help_text",
                            versions: ["1.0", "2.0", "3.0"],
                        },
                        outputs: [],
                        postJobActions: [],
                    };
                },
                getManager: () => {
                    return {
                        nodes: [],
                    };
                },
            },
            localVue,
            stubs: {
                CurrentUser: MockCurrentUser({ id: "fakeuser" }),
                ConfigProvider: MockConfigProvider({ id: "fakeconfig" }),
                FormElement: { template: "<div>form-element</div>" },
                ToolFooter: { template: "<div>tool-footer</div>" },
            },
        });
    });

    it("check props", async () => {
        const dropdowns = wrapper.findAll(".dropdown-item");
        let version = dropdowns.at(3);
        expect(version.text()).toBe("Switch to 2.0");
        let state = wrapper.emitted().onSetData[0][1];
        expect(state.tool_version).toEqual("1.0");
        expect(state.tool_id).toEqual("tool_id+1.0");
        await version.trigger("click");
        state = wrapper.emitted().onSetData[1][1];
        expect(state.tool_version).toEqual("2.0");
        expect(state.tool_id).toEqual("tool_id+2.0");
        version = dropdowns.at(2);
        expect(version.text()).toBe("Switch to 3.0");
        await version.trigger("click");
        state = wrapper.emitted().onSetData[2][1];
        expect(state.tool_version).toEqual("3.0");
        expect(state.tool_id).toEqual("tool_id+3.0");
    });
});
