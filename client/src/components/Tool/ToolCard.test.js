import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import ToolCard from "./ToolCard";

const localVue = getLocalVue();

describe("ToolCard", () => {
    let wrapper;

    beforeEach(() => {
        wrapper = mount(ToolCard, {
            propsData: {
                id: "identifier",
                user: {
                    id: "user.id",
                    email: "user.email",
                    is_admin: true,
                    preferences: {},
                },
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
                },
                messageText: "messageText",
                messageVariant: "warning",
                disabled: false,
            },
            stubs: {
                ToolSourceMenuItem: { template: "<div></div>" },
            },
            localVue,
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
