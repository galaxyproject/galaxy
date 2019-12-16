import { shallowMount } from "@vue/test-utils";
import Details from "./Details";
import { __RewireAPI__ as rewire } from "./Details";
import Vue from "vue";

describe("Details", () => {
    beforeEach(() => {
        rewire.__Rewire__(
            "Services",
            class {
                async getRepositoryByName(url, name, owner) {
                    expect(url).to.equal("tool_shed_url");
                    expect(name).to.equal("name");
                    expect(owner).to.equal("owner");
                    return {};
                }
            }
        );
    });

    it("test repository details loading", async () => {
        const wrapper = shallowMount(Details, {
            propsData: {
                repo: {
                    tool_shed_url: "tool_shed_url",
                    name: "name",
                    owner: "owner"
                }
            }
        });
        expect(wrapper.findAll("loading-span-stub").length).to.equal(1);
        expect(wrapper.find("loading-span-stub").attributes("message")).to.equal(
            "Loading installed repository details"
        );
        expect(wrapper.findAll("repositorydetails-stub").length).to.equal(0);
        await Vue.nextTick();
        expect(wrapper.findAll("loading-span-stub").length).to.equal(0);
        expect(wrapper.findAll(".alert").length).to.equal(0);
        expect(wrapper.findAll("repositorydetails-stub").length).to.equal(1);
    });
});
