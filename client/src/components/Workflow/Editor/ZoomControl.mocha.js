import Vue from "vue";
import { mount } from "@vue/test-utils";
import ZoomControl from "./ZoomControl";

describe("ZoomControl", () => {
    it("test zoom control", async () => {
        const wrapper = mount(ZoomControl, {
            propsData: {
                zoomLevel: 10,
            },
        });
        const buttons = wrapper.findAll("button");
        expect(buttons.length).to.equal(3);
        buttons.at(0).trigger("click");
        await Vue.nextTick();
        expect(wrapper.emitted().onZoom[0][0]).to.equal(9);
        buttons.at(1).trigger("click");
        await Vue.nextTick();
        expect(wrapper.emitted().onZoom[1][0]).to.equal(10);
        buttons.at(2).trigger("click");
        await Vue.nextTick();
        expect(wrapper.emitted().onZoom[2][0]).to.equal(11);
    });
});
