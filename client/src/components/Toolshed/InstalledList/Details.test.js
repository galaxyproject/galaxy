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
                    expect(url).toBe("tool_shed_url");
                    expect(name).toBe("name");
                    expect(owner).toBe("owner");
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
                    owner: "owner",
                },
            },
        });
        expect(wrapper.findAll("loading-span-stub").length).toBe(1);
        expect(wrapper.find("loading-span-stub").attributes("message")).toBe("Loading installed repository details");
        expect(wrapper.findAll("repositorydetails-stub").length).toBe(0);
        await Vue.nextTick();
        expect(wrapper.findAll("loading-span-stub").length).toBe(0);
        expect(wrapper.findAll(".alert").length).toBe(0);
        expect(wrapper.findAll("repositorydetails-stub").length).toBe(1);
    });
});
