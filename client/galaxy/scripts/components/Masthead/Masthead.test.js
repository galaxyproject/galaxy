import Masthead from "./Masthead.vue";
import { mount, createLocalVue } from "@vue/test-utils";
import Scratchbook from "layout/scratchbook";

describe("Masthead.vue", () => {
    let wrapper;
    let localVue;
    let scratchbook;
    let quotaRendered, quotaEl;

    beforeEach(() => {
        localVue = createLocalVue();
        quotaRendered = false;
        quotaEl = null;

        const quotaMeter = {
            setElement: function (el) {
                quotaEl = el;
            },
            render: function () {
                quotaRendered = true;
            },
        };

        const tabs = [
            // Main Analysis Tab..
            {
                id: "analysis",
                title: "Analyze",
                menu: false,
                url: "root",
            },
            {
                id: "shared",
                title: "Shared Items",
                menu: [{ title: "_menu_title", url: "_menu_url", target: "_menu_target" }],
            },
            // Hidden tab (pre-Vue framework supported this, not sure it is used
            // anywhere?)
            {
                id: "hiddentab",
                title: "Hidden Title",
                menu: false,
                hidden: true,
            },
        ];
        const activeTab = "shared";

        // scratchbook assumes this is a Backbone collection - mock that out.
        tabs.add = (x) => {
            tabs.push(x);
            return x;
        };
        scratchbook = new Scratchbook({
            collection: tabs,
        });
        const frames = scratchbook.getFrames();

        wrapper = mount(Masthead, {
            propsData: {
                quotaMeter,
                frames,
                tabs,
                activeTab,
                appRoot: "prefix/",
            },
            localVue,
            attachToDocument: true,
        });
    });

    it("set quota element and renders it", () => {
        expect(quotaEl).to.not.equals(null);
        expect(quotaRendered).to.equals(true);
    });

    it("should render simple tab item links", () => {
        expect(wrapper.findAll("li.nav-item").length).to.equals(5);
        // Ensure specified link title respected.
        expect(wrapper.find("#analysis a").text()).to.equals("Analyze");
        expect(wrapper.find("#analysis a").attributes("href")).to.equals("prefix/root");
    });

    it("should render tab items with menus", () => {
        // Ensure specified link title respected.
        expect(wrapper.find("#shared a").text()).to.equals("Shared Items");
        expect(wrapper.find("#shared").classes("dropdown")).to.equals(true);

        expect(wrapper.findAll("#shared .dropdown-menu li").length).to.equals(1);
        expect(wrapper.find("#shared .dropdown-menu li a").attributes().href).to.equals("prefix/_menu_url");
        expect(wrapper.find("#shared .dropdown-menu li a").attributes().target).to.equals("_menu_target");
        expect(wrapper.find("#shared .dropdown-menu li a").text()).to.equals("_menu_title");
    });

    it("should make hidden tabs hidden", () => {
        expect(wrapper.find("#analysis").attributes().style).to.not.contain("display: none");
        expect(wrapper.find("#hiddentab").attributes().style).to.contain("display: none");
    });

    it("should highlight the active tab", () => {
        expect(wrapper.find("#analysis").classes("active")).to.equals(false);
        expect(wrapper.find("#shared").classes("active")).to.equals(true);
    });

    it("should display scratchbook button", async () => {
        expect(wrapper.find("#enable-scratchbook a span").classes("fa-th")).to.equals(true);
        expect(scratchbook.active).to.equals(false);
        // wrapper.find("#enable-scratchbook a").trigger("click");
        // await localVue.nextTick();
        // expect(scratchbook.active).to.equals(true);
    });
});
