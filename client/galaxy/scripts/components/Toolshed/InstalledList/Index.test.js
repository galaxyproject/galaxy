import { mount } from "@vue/test-utils";
import Index from "./Index";
import { __RewireAPI__ as rewire } from "./Index";
import Vue from "vue";

describe("InstalledList", () => {
    beforeEach(() => {
        rewire.__Rewire__(
            "Services",
            class {
                async getInstalledRepositories() {
                    return [
                        {
                            name: "name_0",
                            description: "description_0"
                        },
                        {
                            name: "name_1",
                            description: "description_1"
                        }
                    ];
                }
            }
        );
    });

    it("test installed list", async () => {
        const wrapper = mount(Index, {
            propsData: {
                filter: ""
            },
            stubs: {
                RepositoryDetails: true
            }
        });
        expect(wrapper.find(".loading-message").text()).to.equal("Loading installed repositories...");
        await Vue.nextTick();
        expect(wrapper.find(".installed-message").text()).to.equal("2 repositories installed on this instance.");
        const links = wrapper.findAll("a");
        expect(links.length).to.equal(2);
        expect(links.at(0).text()).to.equal("name_0");
        expect(links.at(1).text()).to.equal("name_1");
    });
});
