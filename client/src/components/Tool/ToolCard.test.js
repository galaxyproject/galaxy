import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { useUserStore } from "stores/userStore";
import { getLocalVue } from "tests/jest/helpers";
import { setupMockConfig } from "tests/jest/mockConfig";

import { useServerMock } from "@/api/client/__mocks__";

import ToolCard from "./ToolCard";

const { server, http } = useServerMock();

jest.mock("@/api/schema");

const config = { enable_tool_source_display: false };
setupMockConfig(config);

const localVue = getLocalVue();

describe("ToolCard", () => {
    let wrapper;
    let axiosMock;
    let userStore;

    beforeEach(async () => {
        // some child component must be bypassing useConfig - so we need to explicitly
        // stup the API endpoint also. If you can drop this without request problems in log,
        // this hack can be removed.
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response(200).json(config);
            })
        );
        axiosMock = new MockAdapter(axios);
        axiosMock.onGet(`/api/webhooks`).reply(200, []);

        const pinia = createPinia();

        wrapper = mount(ToolCard, {
            propsData: {
                id: "identifier",
                version: "version",
                title: "title",
                description: "description",
                sustainVersion: false,
                options: {
                    id: "options.id",
                    name: "options.name",
                    version: "options.version",
                    versions: [],
                    sharable_url: "options.sharable_url",
                    help: "options.help",
                    help_format: "restructuredtext",
                    citations: false,
                },
                messageText: "messageText",
                messageVariant: "warning",
                disabled: false,
            },
            stubs: {
                ToolSourceMenuItem: { template: "<div></div>" },
            },
            localVue,
            pinia,
        });
        userStore = useUserStore();
        userStore.currentUser = {
            id: "user.id",
            email: "user.email",
            is_admin: true,
            preferences: {},
        };
        await flushPromises();
    });

    it("shows props", async () => {
        const title = wrapper.find("h1");
        expect(title.text()).toBe("title");

        const description = wrapper.find("span[itemprop='description']");
        expect(description.text()).toBe("description");

        const dropdownHeader = wrapper.find(".tool-dropdown");
        expect(dropdownHeader.attributes("title")).toBe("Options");

        const dropdownItems = wrapper.findAll(".dropdown-item");
        expect(dropdownItems.length).toBe(5);

        const backdrop = wrapper.findAll(".portlet-backdrop");
        expect(backdrop.length).toBe(0);

        await wrapper.setProps({ disabled: true });
        const backdropActive = wrapper.findAll(".portlet-backdrop");
        expect(backdropActive.length).toBe(1);
        await flushPromises();
    });
});
