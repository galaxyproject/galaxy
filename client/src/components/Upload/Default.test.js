import Default from "./Default.vue";
import { mountWithApp } from "./test_helpers";
import { __RewireAPI__ as rewire } from "./Default";
import Backbone from "backbone";

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
        expect(wrapper.find("#btn-reset").classes()).to.contain("disabled");
        expect(wrapper.find("#btn-start").classes()).to.contain("disabled");
        expect(wrapper.find("#btn-stop").classes()).to.contain("disabled");
    });

    it("does render FTP is site set", async () => {
        const { wrapper, localVue } = mountWithApp(Default);
        expect(wrapper.find("#btn-ftp").isVisible()).to.equals(true);
        wrapper.find("#btn-ftp").trigger("click");
        await localVue.nextTick();
        // TODO: test popover appears... not sure best way to do this...
    });

    it("doesn't render FTP is no site set", async () => {
        const { wrapper } = mountWithApp(Default, {
            currentFtp: () => {
                return null;
            },
        });
        expect(wrapper.findAll("#btn-ftp").length).to.equals(0);
    });

    it("resets properly", async () => {
        const { wrapper, localVue } = mountWithApp(Default);
        expect(wrapper.vm.showHelper).to.equals(true);
        await localVue.nextTick();
        wrapper.find("#btn-new").trigger("click");
        await localVue.nextTick();
        expect(wrapper.vm.showHelper).to.equals(false);
        expect(wrapper.vm.counterAnnounce).to.equals(1);
        wrapper.find("#btn-reset").trigger("click");
        await localVue.nextTick();
        expect(wrapper.vm.showHelper).to.equals(true);
    });

    it("renders a limitloader element if lazyLoadMax set", async () => {
        const { wrapper } = mountWithApp(Default, {}, { lazyLoadMax: 2 });
        expect(wrapper.findAll(".ui-limitloader").length).to.equals(1);
        // hard to actually test the functionality like in Collection.test.js
        // because we're stubbing out all of UploadRow.
    });
});
