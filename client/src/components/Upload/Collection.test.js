import Collection from "./Collection.vue";
import { mountWithDetails } from "./testHelpers";

describe("Collection.vue", () => {
    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithDetails(Collection);
        expect(wrapper.vm.counterAnnounce).toBe(0);
        expect(wrapper.vm.showHelper).toBe(true);
        expect(wrapper.vm.extensions[0].id).toBe("ab1");
        expect(wrapper.find("#btn-reset").classes()).toEqual(expect.arrayContaining(["disabled"]));
        expect(wrapper.find("#btn-start").classes()).toEqual(expect.arrayContaining(["disabled"]));
        expect(wrapper.find("#btn-stop").classes()).toEqual(expect.arrayContaining(["disabled"]));
        expect(wrapper.findAll(".ui-limitloader").length).toBe(0);
    });

    it("does render FTP is site set", async () => {
        const { wrapper } = mountWithDetails(Collection);
        expect(wrapper.find("#btn-ftp").element).toBeVisible();
    });

    it("doesn't render FTP is no site set", async () => {
        const { wrapper } = mountWithDetails(Collection, {
            currentFtp: null,
        });
        expect(wrapper.findAll("#btn-ftp").length).toBe(0);
    });

    it("resets properly", async () => {
        const { wrapper, localVue } = mountWithDetails(Collection);
        expect(wrapper.vm.showHelper).toBe(true);
        await localVue.nextTick();
        await wrapper.find("#btn-new").trigger("click");
        expect(wrapper.vm.showHelper).toBe(false);
        expect(wrapper.vm.counterAnnounce).toBe(1);

        expect(wrapper.find("#btn-reset").classes()).toEqual(expect.not.arrayContaining(["disabled"]));
        expect(wrapper.find("#btn-start").classes()).toEqual(expect.not.arrayContaining(["disabled"]));

        await wrapper.find("#btn-reset").trigger("click");
        expect(wrapper.vm.showHelper).toBe(true);
    });

    it("respects lazyLoadMax limit", async () => {
        const { wrapper, localVue } = mountWithDetails(Collection, {}, { lazyLoadMax: 2 });
        expect(wrapper.findAll(".ui-limitloader").length).toBe(1);
        await localVue.nextTick();
        await wrapper.find("#btn-new").trigger("click");
        await wrapper.find("#btn-new").trigger("click");
        expect(wrapper.findAll("table tbody tr").length).toBe(2);
        await wrapper.find("#btn-new").trigger("click");
        expect(wrapper.findAll("table tbody tr").length).toBe(2);
        expect(wrapper.find(".ui-limitloader").text()).toEqual(expect.stringContaining("only the first 2 entries"));
    });
});
