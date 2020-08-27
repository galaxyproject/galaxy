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
                    expect(toolshedUrl).to.equal("toolshedUrl");
                    expect(repositoryId).to.equal("id");
                    return [];
                }
                async getInstalledRepositoriesByName(name, owner) {
                    expect(name).to.equal("name");
                    expect(owner).to.equal("owner");
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
        expect(wrapper.find(".loading-message").text()).to.equal("Loading repository details...");
        await Vue.nextTick();
        expect(wrapper.findAll(".alert").length).to.equal(0);
        await Vue.nextTick();
        expect(wrapper.findAll(".alert").length).to.equal(0);
    });
});
