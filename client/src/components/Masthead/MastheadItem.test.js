import MastheadItem from "./MastheadItem.vue";
import { mount, createLocalVue } from "@vue/test-utils";

describe("Masthead.vue", () => {
    let wrapper;
    let localVue;
    let active, menu;

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
        });
    }

    it("should render active tab with menus", async () => {
        active = "mytab";
        menu = true;
        wrapper = m();
        expect(wrapper.vm.active).to.equals(true);
        expect(wrapper.vm.menu).to.equals(true);
    });

    it("should render inactive tabs without menus", async () => {
        active = "othertab";
        menu = false;
        wrapper = m();
        expect(wrapper.vm.active).to.equals(false);
        expect(wrapper.vm.menu).to.equals(false);
    });
});
