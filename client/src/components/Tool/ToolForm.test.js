import { mount } from "@vue/test-utils";
import MockCurrentHistory from "components/providers/MockCurrentHistory";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { useHistoryStore } from "stores/historyStore";
import { useUserStore } from "stores/userStore";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";

import ToolForm from "./ToolForm";

const { server, http } = useServerMock();

const localVue = getLocalVue();
const pinia = createPinia();

describe("ToolForm", () => {
    let wrapper;
    let userStore;
    let historyStore;

    beforeEach(() => {
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json({
                    enable_tool_source_display: false,
                    object_store_allows_id_selection: false,
                });
            }),

            http.get("/api/tools/{tool_id}/build", ({ response }) => {
                return response(200).json({
                    id: "tool_id",
                    name: "tool_name",
                    version: "version",
                    inputs: [],
                    help: "help_text",
                    creator: [
                        { class: "Person", givenName: "FakeName", familyName: "FakeSurname", email: "fakeEmail" },
                    ],
                });
            }),

            http.get("/api/tools/{tool_id}/citations", ({ response }) => {
                return response(200).json([]);
            }),

            http.get("/api/webhooks", ({ response }) => {
                return response(200).json([]);
            })
        );

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
        userStore.currentUser = { id: "fakeUser" };
        historyStore = useHistoryStore();
        historyStore.setHistories([{ id: "fakeHistory" }]);
        historyStore.setCurrentHistoryId("fakeHistory");
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
