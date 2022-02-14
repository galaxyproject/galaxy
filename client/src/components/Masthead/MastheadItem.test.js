import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import MastheadItem from "./MastheadItem.vue";

describe("MastheadItem.vue", () => {
    let wrapper;
    let localVue;
    let active;
    let menu;

    beforeEach(() => {
        localVue = getLocalVue();
    });

    function m() {
        const tab = {
            id: "mytab",
            menu: menu,
        };

        return shallowMount(MastheadItem, {
            propsData: {
                tab,
                activeTab: active,
            },
            localVue,
        });
    }

    it("should render active tab with menus", async () => {
        active = "mytab";
        menu = true;
        wrapper = m();
        expect(wrapper.vm.classes.active).toBe(true);
        expect(wrapper.vm.menu).toBe(true);
    });

    it("should render inactive tabs without menus", async () => {
        active = "othertab";
        menu = false;
        wrapper = m();
        expect(wrapper.vm.classes.active).toBe(false);
        expect(wrapper.vm.menu).toBe(false);
    });
});
