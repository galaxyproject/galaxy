import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";

import DataDialogSearch from "./DataDialogSearch.vue";
import DatasetCollectionDialog from "./DatasetCollectionDialog.vue";
import SelectionDialog from "./SelectionDialog.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GTable from "@/components/Common/GTable.vue";

vi.mock("app");

const { server, http } = useServerMock();

const mockOptions = {
    callback: () => {},
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
        expect(wrapper.findComponent(GTable).exists()).toBe(false);

        await flushPromises();

        expect(wrapper.findComponent(GAlert).exists()).toBe(false);
        expect(wrapper.findComponent(GTable).exists()).toBe(true);
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
        expect(wrapper.findComponent(GAlert).text()).toBe("Bad error");
    });

    describe("with many collections", () => {
        beforeEach(() => {
            const collections = Array.from({ length: 30 }, (_, index) => ({
                id: `c${index + 1}`,
                name: `collection ${index + 1}`,
                hid: index + 1,
            }));
            server.use(
                http.untyped.get(`/api/histories/${mockOptions.history}/contents`, () =>
                    HttpResponse.json(collections),
                ),
            );
        });

        function rowLabels() {
            return wrapper.findAll("td[id^='g-table-cell-label-']").map((cell) => cell.text());
        }

        it("pages the collections, newest first", async () => {
            wrapper = mount(DatasetCollectionDialog, { props: mockOptions, global: localVue });
            await flushPromises();
            expect(rowLabels()).toHaveLength(25);
            expect(rowLabels()[0]).toBe("collection 30");
            expect(wrapper.text()).not.toContain("No entries.");

            await wrapper.find("[aria-label='Go to page 2']").trigger("click");
            expect(rowLabels()).toEqual([
                "collection 5",
                "collection 4",
                "collection 3",
                "collection 2",
                "collection 1",
            ]);
        });

        it("searches the collections by name", async () => {
            wrapper = mount(DatasetCollectionDialog, { props: mockOptions, global: localVue });
            await flushPromises();

            wrapper.findComponent(DataDialogSearch).vm.$emit("input", "collection 1");
            await flushPromises();
            expect(rowLabels()).toEqual([
                "collection 19",
                "collection 18",
                "collection 17",
                "collection 16",
                "collection 15",
                "collection 14",
                "collection 13",
                "collection 12",
                "collection 11",
                "collection 10",
                "collection 1",
            ]);
            expect(wrapper.find("[aria-label='Go to page 2']").exists()).toBe(false);
        });
    });
});
