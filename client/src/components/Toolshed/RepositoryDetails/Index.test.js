import { mount } from "@vue/test-utils";
import Index from "./Index";
import { __RewireAPI__ as rewire } from "./Index";
import Vue from "vue";

describe("RepositoryDetails", () => {
    beforeEach(() => {
        rewire.__Rewire__(
            "Services",
            class {
                async getRepository(toolshedUrl, repositoryId) {
                    expect(toolshedUrl).toBe("toolshedUrl");
                    expect(repositoryId).toBe("id");
                    return [];
                }
                async getInstalledRepositoriesByName(name, owner) {
                    expect(name).toBe("name");
                    expect(owner).toBe("owner");
                    return [];
                }
            }
        );
    });

    it("test repository details index", async () => {
        const wrapper = mount(Index, {
            propsData: {
                repo: {
                    id: "id",
                    name: "name",
                    owner: "owner",
                    description: "description",
                },
                toolshedUrl: "toolshedUrl",
            },
            stubs: {
                RepositoryDetails: true,
                InstallationSettings: true,
                RepositoryTools: true,
            },
        });
        expect(wrapper.find(".loading-message").text()).toBe("Loading repository details...");
        await Vue.nextTick();
        expect(wrapper.findAll(".alert").length).toBe(0);
        await Vue.nextTick();
        expect(wrapper.findAll(".alert").length).toBe(0);
    });
});
