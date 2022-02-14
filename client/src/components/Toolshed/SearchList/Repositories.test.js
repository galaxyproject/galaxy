import { mount, createLocalVue } from "@vue/test-utils";
import Repositories from "./Repositories";

jest.mock("app");

import { Services } from "../services";
jest.mock("../services");

Services.mockImplementation(() => {
    return {
        async getRepositories() {
            return [
                {
                    name: "name_0",
                    owner: "owner_0",
                    last_updated: "last_updated_0",
                    times_downloaded: "times_downloaded_0",
                },
                {
                    name: "name_1",
                    owner: "owner_1",
                    last_updated: "last_updated_1",
                    times_downloaded: "times_downloaded_1",
                },
            ];
        },
    };
});

describe("Repositories", () => {
    const localVue = createLocalVue();

    it("test repository details loading", async () => {
        const wrapper = mount(Repositories, {
            propsData: {
                query: "toolname",
                scrolled: false,
                toolshedUrl: "toolshedUrl",
            },
            localVue,
        });
        // Test initial state prior to the data fetch tick -- should be loading.
        expect(wrapper.find(".loading-message").text()).toBe("Loading repositories...");
        await localVue.nextTick();
        const links = wrapper.findAll("a");
        expect(links.length).toBe(2);
        expect(links.at(0).text()).toBe("name_0");
        expect(links.at(1).text()).toBe("name_1");
        // Reset repositories and state to test empty.
        wrapper.vm.repositories = [];
        wrapper.vm.pageState = 2; // COMPLETE is '2'
        await localVue.nextTick();
        expect(wrapper.find(".unavailable-message").text()).toBe("No matching repositories found.");
    });
});
