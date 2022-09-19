import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import ToolCard from "./ToolCard";
import Vuex from "vuex";
import { userStore } from "store/userStore";
import { configStore } from "store/configStore";

const localVue = getLocalVue();

const createStore = (currentUser) => {
    return new Vuex.Store({
        modules: {
            user: {
                state: {
                    currentUser,
                },
                getters: userStore.getters,
                actions: {
                    loadUser: jest.fn(),
                },
                namespaced: true,
            },
            config: {
                state: {
                    config: {},
                },
                getters: configStore.getters,
                actions: {
                    loadConfigs: jest.fn(),
                },
                namespaced: true,
            },
        },
    });
};

describe("ToolCard", () => {
    let wrapper;

    beforeEach(() => {
        const store = createStore({
            id: "user.id",
            email: "user.email",
            preferences: {},
        });

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
                    citations: null,
                    hasCitations: false,
                },
                messageText: "messageText",
                messageVariant: "warning",
                disabled: false,
            },
            stubs: {
                ToolSourceMenuItem: { template: "<div></div>" },
            },
            localVue,
            store,
            provide: { store },
        });
    });

    it("check props", async () => {
        const title = wrapper.find(".portlet-title-text > b");
        expect(title.text()).toBe("title");
        const description = wrapper.find(".portlet-title-text > span");
        expect(description.text()).toBe("description");
        const icon = wrapper.find(".portlet-title-icon");
        expect(icon.classes()).toContain("fa-wrench");
        const dropdownHeader = wrapper.find(".tool-dropdown");
        expect(dropdownHeader.attributes("title")).toBe("Options");
        const dropdownItems = wrapper.findAll(".dropdown-item");
        expect(dropdownItems.length).toBe(4);
        const backdrop = wrapper.findAll(".portlet-backdrop");
        expect(backdrop.length).toBe(0);
        await wrapper.setProps({ disabled: true });
        const backdropActive = wrapper.findAll(".portlet-backdrop");
        expect(backdropActive.length).toBe(1);
    });
});
