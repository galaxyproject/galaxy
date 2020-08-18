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
import { getNewAttachNode } from "jest/helpers";

const localVue = createLocalVue();
localVue.use(BootstrapVue);
localVue.filter("localize", (value) => _l(value));

describe("CloudAuth component", () => {
    let stub;
    let wrapper;

    const mockSvc = {
        listCredentials: async () => null,
    };

    rewire.__Rewire__("svc", mockSvc);

    beforeEach(async () => {
        const creds = listCredentials.map(Credential.create);
        stub = sinon.stub(mockSvc, "listCredentials").resolves(creds);
        wrapper = shallowMount(CloudAuth, { localVue, attachTo: getNewAttachNode() });
        await flushPromises();
    });

    afterEach(() => {
        if (stub) {
            stub.restore();
        }
    });

    describe("initialization", () => {
        it("should render the initial list", () => {
            expect(wrapper).toBeTruthy();
            expect(wrapper.findComponent(CloudAuthItem).exists()).toBeTruthy();
            expect(wrapper.vm.items.length == 2).toBeTruthy();
            expect(wrapper.vm.filteredItems.length == 2).toBeTruthy();
        });
    });

    describe("text filter", () => {
        it("should show filter result by text match", () => {
            let results;

            wrapper.vm.filter = "aws";
            results = wrapper.vm.filteredItems;
            expect(wrapper.findComponent(CloudAuthItem).exists()).toBeTruthy();
            expect(results.length == 1).toBeTruthy();

            wrapper.vm.filter = "azure";
            results = wrapper.vm.filteredItems;
            expect(results.length == 1).toBeTruthy();

            wrapper.vm.filter = "";
            results = wrapper.vm.filteredItems;
            expect(results.length == 2).toBeTruthy();
        });
    });

    describe("create button", () => {
        it("clicking create button should add a blank key", () => {
            let results = wrapper.vm.filteredItems;
            expect(wrapper.findComponent(CloudAuthItem).exists()).toBeTruthy();
            expect(results.length == 2).toBeTruthy();

            const button = wrapper.find("button[name=createNewKey]");
            expect(button).toBeTruthy();
            button.trigger("click");

            results = wrapper.vm.filteredItems;
            expect(results.length == 3).toBeTruthy();

            const blank = results.find((i) => i.id == null);
            expect(blank).toBeTruthy();
            expect(blank.id == null).toBeTruthy();
        });
    });
});
