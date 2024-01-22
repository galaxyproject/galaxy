import { mount } from "@vue/test-utils";
import axios from "axios";
import MockAdapter from "axios-mock-adapter";
import { createPinia } from "pinia";
import { useUserStore } from "stores/userStore";
import { getLocalVue } from "tests/jest/helpers";

import ToolCard from "./ToolCard";

jest.mock("@/api/schema");

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: { enable_tool_source_display: false },
        isConfigLoaded: true,
    })),
}));

const localVue = getLocalVue();

describe("ToolCard", () => {
    let wrapper;
    let axiosMock;
    let userStore;

    beforeEach(() => {
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
                    versions: [],
                    sharable_url: "options.sharable_url",
                    help: "options.help",
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
    });
});
