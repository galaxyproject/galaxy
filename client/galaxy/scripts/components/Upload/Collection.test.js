import Collection from "./Collection.vue";
import { mountWithApp } from "./test_helpers";

describe("Collection.vue", () => {
    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithApp(Collection);
        expect(wrapper.vm.counterAnnounce).to.equals(0);
        expect(wrapper.vm.showHelper).to.equals(true);
        expect(wrapper.vm.extensions[0].id).to.equals("ab1");
    });

    it("does render FTP is site set", async () => {
        const { wrapper } = mountWithApp(Collection);
        expect(wrapper.find("#btn-ftp").isVisible()).to.equals(true);
    });

    it("doesn't render FTP is no site set", async () => {
        const { wrapper } = mountWithApp(Collection, {
            currentFtp: () => {
                return null;
            }
        });
        expect(wrapper.findAll("#btn-ftp").length).to.equals(0);
    });

    it("resets properly", async () => {
        const { wrapper, localVue } = mountWithApp(Collection);
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
