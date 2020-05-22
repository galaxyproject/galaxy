import _ from "underscore";
import Backbone from "backbone";
import "utils/uploadbox";
import { mount, createLocalVue } from "@vue/test-utils";

export function mountWithApp(component, options = {}, propsData_ = {}) {
    const app = _.defaults(options, {
        defaultExtension: "auto",
        currentFtp: () => {
            return "ftp://localhost";
        },
        model: new Backbone.Model(),
        listExtensions: [
            { id: "ab1", text: "ab1", description: "A binary sequence file in 'ab1' format with a '.ab1'" },
            {
                id: "affybatch",
                text: "affybatch",
                description: null,
                composite_files: [
                    {
                        name: "%s.pheno",
                        optional: false,
                        description: "Phenodata tab text file",
                    },
                    {
                        name: "%s.affybatch",
                        optional: false,
                        description: "AffyBatch R object saved to file",
                    },
                ],
            },
        ],
    });
    const propsData = _.defaults(propsData_, { app });
    const localVue = createLocalVue();
    const wrapper = mount(component, {
        propsData,
        localVue,
        attachToDocument: true,
        stubs: {
            select2: true,
        },
    });
    return { wrapper, localVue };
}
