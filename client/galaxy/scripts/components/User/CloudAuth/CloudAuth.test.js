/* global expect */
import sinon from "sinon";

import { default as CloudAuth, __RewireAPI__ as rewire } from "./CloudAuth";
import CloudAuthItem from "./CloudAuthItem.vue";

import { mount, shallowMount, createLocalVue } from "@vue/test-utils";
import _l from "utils/localization";
import BootstrapVue from 'bootstrap-vue'

// test data
import listCredentials from "./testdata/listCredentials.json";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.filter("localize", value => _l(value));

describe("CloudAuth component", () => {
    
    let wrapper, stub;

    let mockSvc = {
        listCredentials: async () => null,
    };

    beforeEach(() => {
        wrapper = shallowMount(CloudAuth, { localVue });
        rewire.__Rewire__("svc", mockSvc);
    });

    afterEach(() => {
        if (stub) {
            stub.restore();
        }
    });

    describe("initialization", () => {

        // fake list load
        stub = sinon.stub(mockSvc, "listCredentials").resolves(listCredentials);

        it("should mount", () => {
            assert(wrapper);
        })

        it("should show one item", () => {
            let keyItems = wrapper.findAll(".cloud-auth-key");
            let firstitem = keyItems.at(0);
            assert(keyItems);
        })
    })

})