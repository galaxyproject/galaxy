import "utils/uploadbox";
import _ from "underscore";
import { mount, createLocalVue } from "@vue/test-utils";

export function mountWithApp(component, options = {}) {
    const app = _.defaults(options, {
        defaultExtension: "auto",
        currentFtp: () => {
            return "ftp://localhost";
        }
    });
    const propsData = { app };
    const localVue = createLocalVue();
    const wrapper = mount(component, {
        propsData,
        localVue,
        attachToDocument: true,
        stubs: {
            select2: true
        }
    });
    return { wrapper, localVue };
}
