import Composite from "./Composite.vue";
import { mountWithDetails } from "./testHelpers";

describe("Composite.vue", () => {
    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithDetails(Composite);
        expect(wrapper.find("#btn-start").classes()).toEqual(expect.arrayContaining(["disabled"]));
        expect(wrapper.vm.showHelper).toBe(true);
        expect(wrapper.vm.readyStart).toBe(false);
        // filters listExtensions to just the composite definition + _select_ value
        const extensions = wrapper.vm.extensions;
        expect(extensions.length).toBe(2);
        expect(extensions[0].id).toBe("_select_");
        expect(extensions[1].id).toBe("affybatch");
    });
});
