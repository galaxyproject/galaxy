import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { BAlert, BTable } from "bootstrap-vue";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import DatasetCollectionDialog from "./DatasetCollectionDialog.vue";
import SelectionDialog from "./SelectionDialog.vue";

vi.mock("app");

const { server, http } = useServerMock();

const mockOptions = {
    callback: () => {},
    modalStatic: true,
    history: "f2db41e1fa331b3e",
};

describe("DatasetCollectionDialog.vue", () => {
    let wrapper;
    let localVue;

    beforeEach(() => {
        localVue = getLocalVue();
    });

    it("loads correctly in loading state, shows options when optionsShow becomes true", async () => {
        // Initially in loading state.
        const collectionsResponse = [{ id: "f2db41e1fa331b3e", name: "Awesome Collection", hid: 1 }];
        server.use(
            http.untyped.get(`/api/histories/${mockOptions.history}/contents`, ({ request }) => {
                const url = new URL(request.url);
                if (url.searchParams.get("type") === "dataset_collection") {
                    return HttpResponse.json(collectionsResponse);
                }
                return HttpResponse.json([]);
            }),
        );

        wrapper = mount(DatasetCollectionDialog, {
            props: mockOptions,
            global: localVue,
        });

        expect(wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        expect(wrapper.findComponent(BTable).exists()).toBe(false);

        await flushPromises();

        expect(wrapper.findComponent(BAlert).exists()).toBe(false);
        expect(wrapper.findComponent(BTable).exists()).toBe(true);
    });

    it("error message set on dataset collection fetch problems", async () => {
        server.use(
            http.untyped.get(`/api/histories/${mockOptions.history}/contents`, () => {
                return HttpResponse.json({ err_msg: "Bad error" }, { status: 403 });
            }),
        );
        wrapper = mount(DatasetCollectionDialog, {
            props: mockOptions,
            global: localVue,
        });
        await flushPromises();
        expect(wrapper.findComponent(BAlert).text()).toBe("Bad error");
    });
});
