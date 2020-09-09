import MastheadItem from "./MastheadItem.vue";
import { mount, createLocalVue } from "@vue/test-utils";
import { getNewAttachNode } from "jest/helpers";

describe("Masthead.vue", () => {
    let wrapper;
    let localVue;
    let active;
    let menu;

    beforeEach(() => {
        localVue = createLocalVue();
    });

    function m() {
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
            attachTo: getNewAttachNode(),
        });
    }

    it("should render active tab with menus", async () => {
        active = "mytab";
        menu = true;
        wrapper = m();
        expect(wrapper.vm.active).toBe(true);
        expect(wrapper.vm.menu).toBe(true);
    });

    it("should render inactive tabs without menus", async () => {
        active = "othertab";
        menu = false;
        wrapper = m();
        expect(wrapper.vm.active).toBe(false);
        expect(wrapper.vm.menu).toBe(false);
    });
});
