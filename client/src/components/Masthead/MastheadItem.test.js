import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import MastheadItem from "./MastheadItem.vue";

describe("MastheadItem.vue", () => {
    let wrapper;
    let localVue;

    beforeEach(() => {
        localVue = getLocalVue();
    });

    function m(active, menu) {
        const tab = {
            id: "mytab",
            menu: menu,
        };

        return mount(MastheadItem, {
            propsData: {
                tab,
                activeTab: active,
            },
            localVue,
        });
    }

    it("should render active tab with menus", async () => {
        wrapper = m("mytab", true);
        expect(wrapper.classes("active")).toBe(true);
        expect(wrapper.classes("b-nav-dropdown")).toBe(true);
    });

    it("should render inactive tabs without menus", async () => {
        wrapper = m("othertab", false);
        expect(wrapper.classes("active")).toBe(false);
        expect(wrapper.classes("b-nav-dropdown")).toBe(false);
    });
});
