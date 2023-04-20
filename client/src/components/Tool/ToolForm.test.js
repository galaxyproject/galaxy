import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { mount } from "@vue/test-utils";
import { getLocalVue, mockModule } from "tests/jest/helpers";
import ToolForm from "./ToolForm";
import MockConfigProvider from "../providers/MockConfigProvider";
import MockCurrentHistory from "components/providers/MockCurrentHistory";
import Vue from "vue";
import Vuex from "vuex";
import { createPinia } from "pinia";
import { configStore } from "store/configStore";
import { useUserStore } from "stores/userStore";
import { useHistoryStore } from "stores/historyStore";

const localVue = getLocalVue();
const pinia = createPinia();

describe("ToolForm", () => {
    let wrapper;
    let axiosMock;
    let userStore;
    let historyStore;

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
        axiosMock.onGet(`/api/webhooks`).reply(200, []);

        const citations = [];
        axiosMock.onGet(`/api/tools/tool_id/citations`).reply(200, citations);

        const store = new Vuex.Store({
            modules: {
                config: mockModule(configStore),
            },
        });

        wrapper = mount(ToolForm, {
            propsData: {
                id: "tool_id",
                version: "version",
            },
            localVue,
            stubs: {
                UserHistories: MockCurrentHistory({ id: "fakeHistory" }),
                ConfigProvider: MockConfigProvider({ id: "fakeconfig" }),
                FormDisplay: true,
            },
            store,
            provide: { store },
            pinia,
        });
        userStore = useUserStore();
        userStore.currentUser = { id: "fakeUser" };
        historyStore = useHistoryStore();
        historyStore.setHistories([{ id: "fakeHistory" }]);
        historyStore.setCurrentHistoryId("fakeHistory");
    });

    afterEach(() => {
        axiosMock.restore();
        axiosMock.reset();
    });

    it("shows props", async () => {
        await Vue.nextTick();
        const button = wrapper.find(".btn-primary");
        expect(button.attributes("title")).toBe("Run tool: tool_name (version)");
        const dropdown = wrapper.findAll(".dropdown-item");
        expect(dropdown.length).toBe(2);
        const help = wrapper.find(".form-help");
        expect(help.text()).toBe("help_text");
    });
});
