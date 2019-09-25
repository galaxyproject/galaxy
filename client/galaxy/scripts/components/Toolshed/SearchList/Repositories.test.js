import { mount } from "@vue/test-utils";
import Repositories from "./Repositories";
import { __RewireAPI__ as rewire } from "./Repositories";
import Vue from "vue";

describe("Repositories", () => {
    beforeEach(() => {
        rewire.__Rewire__(
            "Services",
            class {
                async getRepositories() {
                    return [
                        {
                            name: "name_0",
                            owner: "owner_0",
                            last_updated: "last_updated_0",
                            times_downloaded: "times_downloaded_0"
                        },
                        {
                            name: "name_1",
                            owner: "owner_1",
                            last_updated: "last_updated_1",
                            times_downloaded: "times_downloaded_1"
                        }
                    ];
                }
            }
        );
    });

    it("test repository details loading", async () => {
        const wrapper = mount(Repositories, {
            propsData: {
                query: true,
                scrolled: false,
                toolshedUrl: "toolshedUrl"
            }
        });
        expect(wrapper.find(".loading-message").text()).to.equal("Loading repositories...");
        wrapper.vm.pageState = wrapper.vm.COMPLETE;
        expect(wrapper.find(".unavailable-message").text()).to.equal("No matching repositories found.");
        await Vue.nextTick();
        const links = wrapper.findAll("a");
        expect(links.length).to.equal(2);
        expect(links.at(0).text()).to.equal("name_0");
        expect(links.at(1).text()).to.equal("name_1");
    });
});
