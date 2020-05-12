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

        const frames = {
            on: () => {
                return frames;
            },
        };

        wrapper = mount(Masthead, {
            propsData: {
                quotaMeter,
                frames,
            },
            localVue,
            attachToDocument: true,
        });
    });

    it("set quota element and renders it", async () => {
        expect(quotaEl).to.not.equals(null);
        expect(quotaRendered).to.equals(true);
    });
});
