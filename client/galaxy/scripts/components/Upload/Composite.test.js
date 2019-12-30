import Composite from "./Composite.vue";
import { mountWithApp } from "./test_helpers";

describe("Composite.vue", () => {
    it("loads with correct initial state", async () => {
        const { wrapper } = mountWithApp(Composite);
        expect(wrapper.find("#btn-start").classes()).to.contain("disabled");
        expect(wrapper.vm.showHelper).to.equals(true);
        expect(wrapper.vm.readyStart).to.equals(false);
        // filters listExtensions to just the composite definition + _select_ value
        const extensions = wrapper.vm.extensions;
        expect(extensions.length).to.equals(2);
        expect(extensions[0].id).to.equals("_select_");
        expect(extensions[1].id).to.equals("affybatch");
    });
});
