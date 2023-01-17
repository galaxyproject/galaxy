import flushPromises from "flush-promises";
import { shallowMount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import { default as CloudAuth } from "./CloudAuth";
import CloudAuthItem from "./CloudAuthItem";

jest.mock("./model/service", () => ({
    listCredentials: async () => {
        const listCredentials = require("./testdata/listCredentials.json");
        const Credential = require("./model").Credential;
        return listCredentials.map(Credential.create);
    },
}));

const localVue = getLocalVue();

describe("CloudAuth component", () => {
    let wrapper;

    beforeEach(async () => {
        wrapper = shallowMount(CloudAuth, { localVue });
        await flushPromises();
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
