import sinon from "sinon";
import { mount } from "@vue/test-utils";
import DataDialog from "./DataDialog.vue";
import { __RewireAPI__ as rewire } from "./DataDialog";

describe("DataDialog.vue", () => {
    let stub;
    let wrapper;
    let emitted;

    let mockAxios = {
        get: () => null
    };

    let mockGetGalaxyInstanceNoHistory = () => {
        return {}
    };

    beforeEach(() => {
        rewire.__Rewire__("axios", mockAxios);
    });

    afterEach(() => {
        if (stub) stub.restore();
    });

    it("loads correctly, shows alert", () => {
        rewire.__Rewire__("getGalaxyInstance", mockGetGalaxyInstanceNoHistory);
        wrapper = mount(DataDialog, {
            propsData: {
                callback: () => {}
            }
        });
        emitted = wrapper.emitted();
        expect(wrapper.classes()).contain("data-dialog-modal");
        expect(wrapper.find(".alert").text()).to.equals("Datasets not available.");
        expect(wrapper.find(".btn-secondary").text()).to.equals("Clear");
        expect(wrapper.find(".btn-primary").text()).to.equals("Close");
    });
});
