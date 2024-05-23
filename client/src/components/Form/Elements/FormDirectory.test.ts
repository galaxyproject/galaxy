import { getLocalVue } from "@tests/jest/helpers";
import { mount, Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import Vue from "vue";

import { mockFetcher } from "@/api/schema/__mocks__";
import { rootResponse } from "@/components/FilesDialog/testingData";

import FormDirectory from "./FormDirectory.vue";
import FilesDialog from "@/components/FilesDialog/FilesDialog.vue";

const INVALID_PATH = "./];";
const VALID_PATH = "valid_path";
const TEST_DATA = {
    url: "gxfiles://directory/subdirectory",
    protocol: "gxfiles:",
    expectedNumberOfPaths: 4,
    pathChunks: [
        {
            pathChunk: "directory",
        },
        {
            pathChunk: "subdirectory",
        },
    ],
};

const localVue = getLocalVue();

jest.mock("app");
jest.mock("@/api/schema");

describe("DirectoryPathEditableBreadcrumb", () => {
    let wrapper: Wrapper<Vue>;
    let spyOnUrlSet: jest.SpyInstance;
    let spyOnAddPath: jest.SpyInstance;
    let spyOnUpdateURL: jest.SpyInstance;

    const saveNewChunk = async (path: string) => {
        // enter a new path chunk
        const input = wrapper.find("#path-input-breadcrumb");

        await input.setValue(path);

        expect((input.element as HTMLInputElement).value).toBe(path);

        input.trigger("keyup.enter");
        return input;
    };

    beforeEach(async () => {
        const init = async () => {
            // the file dialog modal should exist
            const filesDialogComponent = wrapper.findComponent(FilesDialog);

            expect(filesDialogComponent.exists()).toBe(true);

            filesDialogComponent.vm.callback({ url: TEST_DATA.url });

            // HACK to avoid https://github.com/facebook/jest/issues/2549 (URL implementation is not the same as global node)
            wrapper.vm.pathChunks = TEST_DATA.pathChunks;

            await flushPromises();
        };

        spyOnUrlSet = jest.spyOn(FormDirectory.prototype.methods, "setUrl");
        spyOnAddPath = jest.spyOn(FormDirectory.prototype.methods, "addPath");
        spyOnUpdateURL = jest.spyOn(FormDirectory.prototype.methods, "updateURL");

        mockFetcher.path("/api/remote_files/plugins").method("get").mock({ data: rootResponse });
        mockFetcher.path("/api/configuration").method("get").mock({ data: {} });

        const pinia = createPinia();

        wrapper = mount(FormDirectory as object, {
            propsData: {
                callback: () => {},
            },
            localVue,
            pinia,
        });

        await flushPromises();

        await init();
    });

    it("should render Breadcrumb", async () => {
        // after initial folder is chosen, setUrl() should be called and modal disappear
        expect(spyOnUrlSet).toHaveBeenCalled();
        expect(wrapper.findComponent(FilesDialog).exists()).toBe(false);
        expect(wrapper.find("ol.breadcrumb").exists()).toBe(true);

        await flushPromises();

        // check breadcrumb items
        const breadcrumbPaths = wrapper.findAll("li.breadcrumb-item");
        expect(breadcrumbPaths.length).toBe(TEST_DATA.expectedNumberOfPaths);
        expect(wrapper.find(".pathname").text()).toBe(TEST_DATA.protocol);

        const regularPathElements = wrapper.findAll("li.breadcrumb-item button[disabled='disabled']");
        expect(regularPathElements.length).toBe(TEST_DATA.pathChunks.length);

        const chunks = TEST_DATA.pathChunks.map((e) => e.pathChunk);

        // every item should be rendered
        for (let i = 0; i < regularPathElements.length; i++) {
            const text = regularPathElements.at(i).text();
            expect(chunks.includes(text)).toBe(true);
        }
    });

    it("should prevent invalid Paths", async () => {
        // enter a new path chunk
        const input = await saveNewChunk(INVALID_PATH);

        await flushPromises();

        // after new entry is entered the value of input should be an empty string
        expect((input.element as HTMLInputElement).value).toBe(INVALID_PATH);

        // should be the same name plus additional item
        expect(wrapper.findAll("li.breadcrumb-item").length).toBe(TEST_DATA.expectedNumberOfPaths);
    });

    it("should save and remove new Paths", async () => {
        // enter a new path chunk
        const input = await saveNewChunk(VALID_PATH);

        await flushPromises();

        expect(spyOnAddPath).toHaveBeenCalled();

        // after new entry is entered the value of input should be an empty string
        expect((input.element as HTMLInputElement).value).toBe("");

        // should be the same name plus additional item
        expect(wrapper.findAll("li.breadcrumb-item").length).toBe(TEST_DATA.expectedNumberOfPaths + 1);

        // find newly added chunk
        const addedChunk = wrapper.findAll("li.breadcrumb-item button").wrappers.find((e) => e.text() === VALID_PATH);

        // remove chunk from the path
        await addedChunk?.trigger("click");

        await flushPromises();

        // number of elements should be the same again
        expect(wrapper.findAll("li.breadcrumb-item").length).toBe(TEST_DATA.expectedNumberOfPaths);
    });

    it("should update new path", async () => {
        // enter a new path chunk
        expect(spyOnUpdateURL).toHaveBeenCalled();

        await saveNewChunk(VALID_PATH);

        await flushPromises();

        expect(spyOnUpdateURL).toHaveBeenCalled();
    });
});
