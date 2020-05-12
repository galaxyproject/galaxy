import Masthead from "./Masthead.vue";
import { mount, createLocalVue } from "@vue/test-utils";

describe("Masthead.vue", () => {
    let wrapper;
    let localVue;
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
                menu: true,
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

        const frames = {
            on: () => {
                return frames;
            },
        };

        wrapper = mount(Masthead, {
            propsData: {
                quotaMeter,
                frames,
                tabs,
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
        console.log(wrapper.html());
        expect(wrapper.findAll("li.nav-item").length).to.equals(3);
        // Ensure specified link title respected.
        expect(wrapper.find("#analysis a").text()).to.equals("Analyze");
        expect(wrapper.find("#analysis a").attributes("href")).to.equals("prefix/root");
    });

    it("should render tab items with menus", () => {
        // Ensure specified link title respected.
        expect(wrapper.find("#shared a").text()).to.equals("Shared Items");
        expect(wrapper.find("#shared").classes("dropdown")).to.equals(true);
    });

    it("should make hidden tabs hidden", () => {
        expect(wrapper.find("#analysis").attributes().style).to.not.contain("display: none");
        expect(wrapper.find("#hiddentab").attributes().style).to.contain("display: none");
    });
});
