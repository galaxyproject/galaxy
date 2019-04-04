import sinon from "sinon";
import flushPromises from "flush-promises";
import { shallowMount, createLocalVue } from "@vue/test-utils";

import { default as CloudAuth, __RewireAPI__ as rewire } from "./CloudAuth";
import CloudAuthItem from "./CloudAuthItem";
import { Credential } from "./model";

import _l from "utils/localization";
import BootstrapVue from "bootstrap-vue";

// test data
import listCredentials from "./testdata/listCredentials.json";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.filter("localize", value => _l(value));

describe("CloudAuth component", () => {
    
    let stub, wrapper;

    let mockSvc = {
        listCredentials: async () => null,
    };
    
    rewire.__Rewire__("svc", mockSvc);
    
    beforeEach(async () => {
        let creds = listCredentials.map(Credential.create);
        stub = sinon.stub(mockSvc, "listCredentials").resolves(creds);
        wrapper = shallowMount(CloudAuth, { localVue });
        await flushPromises();
    });

    afterEach(() => {
        if (stub) {
            stub.restore();
        }
    });
    
    describe("initialization", () => {
        it("should render the initial list", () => {
            assert(wrapper);
            assert(wrapper.contains(CloudAuthItem));
            assert(wrapper.vm.items.length == 2);
            assert(wrapper.vm.filteredItems.length == 2);
        })
    })

    describe("text filter", () => {
        it("should show filter result by text match", () => {

            let results;

            wrapper.vm.filter = "aws";
            results = wrapper.vm.filteredItems;
            assert(wrapper.contains(CloudAuthItem));
            assert(results.length == 1, `Wrong number of items: ${results.length}`);
            
            wrapper.vm.filter = "azure";
            results = wrapper.vm.filteredItems;
            assert(results.length == 1, `Wrong number of items: ${results.length}`);
            
            wrapper.vm.filter = "";
            results = wrapper.vm.filteredItems;
            assert(results.length == 2, `Wrong number of items: ${results.length}`);  
        })
    })

    describe("create button", () => {
        it("clicking create button should add a blank key", () => {
            
            let results = wrapper.vm.filteredItems;
            assert(wrapper.contains(CloudAuthItem));
            assert(results.length == 2, `Wrong number of items: ${results.length}`);
            
            let button = wrapper.find('button[name=createNewKey]');
            assert(button);
            button.trigger('click');

            results = wrapper.vm.filteredItems;
            assert(results.length == 3, `Wrong number of items: ${results.length}`);
            
            let blank = results.find(i => i.id == null);
            assert(blank, "missing blank key");
            assert(blank.id == null);
        })
    })

})