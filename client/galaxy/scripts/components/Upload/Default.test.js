import Default from "./Default.vue";
import { mountWithApp } from "./test_helpers";
import { __RewireAPI__ as rewire } from "./Default";
import Backbone from "Backbone";

describe("Default.vue", () => {
    beforeEach(() => {
        // Use of select2 in default-row requires this mock.
        rewire.__Rewire__("UploadRow", Backbone.View);
    });

    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithApp(Default);
        expect(wrapper.vm.counterAnnounce).to.equals(0);
        expect(wrapper.vm.showHelper).to.equals(true);
        expect(wrapper.vm.extensions[0].id).to.equals("ab1");
    });

    it("resets properly", async () => {
        const { wrapper, localVue } = mountWithApp(Default);
        expect(wrapper.vm.showHelper).to.equals(true);
        wrapper.find("#btn-new").trigger("click");
        await localVue.nextTick();
        expect(wrapper.vm.showHelper).to.equals(false);
        expect(wrapper.vm.counterAnnounce).to.equals(1);
        wrapper.find("#btn-reset").trigger("click");
        await localVue.nextTick();
        expect(wrapper.vm.showHelper).to.equals(true);
    });
});
