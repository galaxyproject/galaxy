import "tests/jest/mockHelpPopovers";

import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue, suppressBootstrapVueWarnings } from "tests/jest/helpers";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import MockCurrentHistory from "@/components/providers/MockCurrentHistory";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import ToolForm from "./ToolForm.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue();
const pinia = createPinia();

// the PersonViewer component uses a BPopover that doesn't work with jsdom properly. It would be
// better to break PersonViewer and OrganizationViewer out into smaller subcomponents and just
// stub out the Popover piece I think.
suppressBootstrapVueWarnings();

describe("ToolForm", () => {
    let wrapper;
    let axiosMock;
    let userStore;
    let historyStore;

    beforeEach(() => {
        // I tried using the useConfig mock and this component seems to bypass that, it would be
        // better if it didn't. We shouldn't have to stub out an API request to get a particular config.
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response.untyped(
                    HttpResponse.json({
                        enable_tool_source_display: false,
                        object_store_allows_id_selection: false,
                    })
                );
            })
        );

        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(`/api/tools/tool_id/build?tool_version=version`).reply(200, {
            id: "tool_id",
            name: "tool_name",
            version: "version",
            inputs: [],
            help: "help_text",
            help_format: "restructuredtext",
            creator: [{ class: "Person", givenName: "FakeName", familyName: "FakeSurname", email: "fakeEmail" }],
        });
        axiosMock.onGet(`/api/webhooks`).reply(200, []);
        axiosMock.onGet(`/api/tools/tool_id/citations`).reply(200, []);

        wrapper = mount(ToolForm, {
            propsData: {
                id: "tool_id",
                version: "version",
            },
            localVue,
            stubs: {
                UserHistories: MockCurrentHistory({ id: "fakeHistory" }),
                FormDisplay: true,
            },
            pinia,
        });
        userStore = useUserStore();
        userStore.currentUser = getFakeRegisteredUser({ id: "fakeUser" });

        historyStore = useHistoryStore();
        historyStore.setHistories([{ id: "fakeHistory" }]);
        historyStore.setCurrentHistoryId("fakeHistory");
    });

    afterEach(() => {
        axiosMock.restore();
        axiosMock.reset();
    });

    it("shows props", async () => {
        await flushPromises();
        const button = wrapper.find(".btn-primary");
        expect(button.attributes("title")).toBe("Run tool: tool_name (version)");
        const dropdown = wrapper.findAll(".dropdown-item");
        expect(dropdown.length).toBe(2);
        const help = wrapper.find(".form-help");
        expect(help.text()).toBe("help_text");
        const creator = wrapper.find(".creative-work-creator");
        expect(creator.text()).toContain("FakeName FakeSurname");
    });
});
