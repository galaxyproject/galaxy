import Collection from "./Collection.vue";
import { mountWithApp } from "./test_helpers";

describe("Collection.vue", () => {
    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithApp(Collection);
        expect(wrapper.vm.counterAnnounce).to.equals(0);
        expect(wrapper.vm.showHelper).to.equals(true);
        expect(wrapper.vm.extensions[0].id).to.equals("ab1");
        expect(wrapper.find("#btn-reset").classes()).to.contain("disabled");
        expect(wrapper.find("#btn-start").classes()).to.contain("disabled");
        expect(wrapper.find("#btn-stop").classes()).to.contain("disabled");
        expect(wrapper.findAll(".ui-limitloader").length).to.equals(0);
    });

    it("does render FTP is site set", async () => {
        const { wrapper } = mountWithApp(Collection);
        expect(wrapper.find("#btn-ftp").isVisible()).to.equals(true);
    });

    it("doesn't render FTP is no site set", async () => {
        const { wrapper } = mountWithApp(Collection, {
            currentFtp: () => {
                return null;
            },
        });
        expect(wrapper.findAll("#btn-ftp").length).to.equals(0);
    });

    it("resets properly", async () => {
        const { wrapper, localVue } = mountWithApp(Collection);
        expect(wrapper.vm.showHelper).to.equals(true);
        await localVue.nextTick();
        wrapper.find("#btn-new").trigger("click");
        await localVue.nextTick();
        expect(wrapper.vm.showHelper).to.equals(false);
        expect(wrapper.vm.counterAnnounce).to.equals(1);

        expect(wrapper.find("#btn-reset").classes()).to.not.contain("disabled");
        expect(wrapper.find("#btn-start").classes()).to.not.contain("disabled");

        wrapper.find("#btn-reset").trigger("click");
        await localVue.nextTick();
        expect(wrapper.vm.showHelper).to.equals(true);
    });

    it("respects lazyLoadMax limit", async () => {
        const { wrapper, localVue } = mountWithApp(Collection, {}, { lazyLoadMax: 2 });
        expect(wrapper.findAll(".ui-limitloader").length).to.equals(1);
        await localVue.nextTick();
        wrapper.find("#btn-new").trigger("click");
        await localVue.nextTick();
        wrapper.find("#btn-new").trigger("click");
        await localVue.nextTick();
        expect(wrapper.findAll("table tbody tr").length).to.equals(2);
        wrapper.find("#btn-new").trigger("click");
        await localVue.nextTick();
        expect(wrapper.findAll("table tbody tr").length).to.equals(2);
        expect(wrapper.find(".ui-limitloader").text()).to.contain("only the first 2 entries");
    });
});
