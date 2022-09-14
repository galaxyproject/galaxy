import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import ToolForm from "./ToolForm";
import MockCurrentUser from "../providers/MockCurrentUser";
import MockConfigProvider from "../providers/MockConfigProvider";
import MockCurrentHistory from "components/providers/MockCurrentHistory";
import Vue from "vue";

const localVue = getLocalVue();

describe("ToolForm", () => {
    let wrapper;
    let axiosMock;

    beforeEach(() => {
        axiosMock = new MockAdapter(axios);

        const toolData = {
            id: "tool_id",
            name: "tool_name",
            version: "version",
            inputs: [],
            help: "help_text",
        };
        axiosMock.onGet(`/api/tools/tool_id/build?tool_version=version`).reply(200, toolData);

        const citations = [];
        axiosMock.onGet(`/api/tools/tool_id/citations`).reply(200, citations);

        wrapper = mount(ToolForm, {
            propsData: {
                id: "tool_id",
                version: "version",
            },
            localVue,
            stubs: {
                CurrentUser: MockCurrentUser({ id: "fakeuser" }),
                UserHistories: MockCurrentHistory({ id: "fakehistory" }),
                ConfigProvider: MockConfigProvider({ id: "fakeconfig" }),
                FormDisplay: true,
            },
        });
    });

    afterEach(() => {
        axiosMock.restore();
        axiosMock.reset();
    });

    it("check props", async () => {
        await Vue.nextTick();
        const button = wrapper.find(".btn-primary");
        expect(button.attributes("title")).toBe("Execute: tool_name (version)");
        const dropdown = wrapper.findAll(".dropdown-item");
        expect(dropdown.length).toBe(2);
        const help = wrapper.find(".form-help");
        expect(help.text()).toBe("help_text");
    });
});
