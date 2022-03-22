import Default from "./Default.vue";
import { mountWithApp } from "./testHelpers";
import Backbone from "backbone";

jest.mock("app");

import UploadRow from "mvc/upload/default/default-row";
jest.mock("mvc/upload/default/default-row");
UploadRow.mockImplementation(Backbone.View);

describe("Default.vue", () => {
    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithApp(Default);
        expect(wrapper.vm.counterAnnounce).toBe(0);
        expect(wrapper.vm.showHelper).toBe(true);
        expect(wrapper.vm.extensions[0].id).toBe("ab1");
        expect(wrapper.find("#btn-reset").classes()).toEqual(expect.arrayContaining(["disabled"]));
        expect(wrapper.find("#btn-start").classes()).toEqual(expect.arrayContaining(["disabled"]));
        expect(wrapper.find("#btn-stop").classes()).toEqual(expect.arrayContaining(["disabled"]));
    });

    it("does render FTP is site set", async () => {
        const { wrapper } = mountWithApp(Default);
        expect(wrapper.find("#btn-ftp").element).toBeVisible();
        await wrapper.find("#btn-ftp").trigger("click");
        // TODO: test popover appears... not sure best way to do this...
    });

    it("doesn't render FTP is no site set", async () => {
        const { wrapper } = mountWithApp(Default, {
            currentFtp: () => {
                return null;
            },
        });
        expect(wrapper.findAll("#btn-ftp").length).toBe(0);
    });

    it("resets properly", async () => {
        const { wrapper, localVue } = mountWithApp(Default);
        expect(wrapper.vm.showHelper).toBe(true);
        await localVue.nextTick();
        await wrapper.find("#btn-new").trigger("click");
        expect(wrapper.vm.showHelper).toBe(false);
        expect(wrapper.vm.counterAnnounce).toBe(1);
        await wrapper.find("#btn-reset").trigger("click");
        expect(wrapper.vm.showHelper).toBe(true);
    });

    it("renders a limitloader element if lazyLoadMax set", async () => {
        const { wrapper } = mountWithApp(Default, {}, { lazyLoadMax: 2 });
        expect(wrapper.findAll(".ui-limitloader").length).toBe(1);
        // hard to actually test the functionality like in Collection.test.js
        // because we're stubbing out all of UploadRow.
    });
});
