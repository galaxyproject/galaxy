import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { rootResponse } from "@/components/FilesDialog/testingData";

import FormDirectory from "./FormDirectory.vue";
import FilesDialog from "@/components/FilesDialog/FilesDialog.vue";

const localVue = getLocalVue();
jest.mock("app");

const { server, http } = useServerMock();

describe("DirectoryPathEditableBreadcrumb", () => {
    let wrapper;
    let spyOnUrlSet;
    let spyOnAddPath;
    let spyOnUpdateURL;

    const testingData = {
        url: "gxfiles://directory/subdirectory",
        protocol: "gxfiles:",
        expectedNumberOfPaths: 4,
        pathChunks: [{ pathChunk: "directory" }, { pathChunk: "subdirectory" }],
    };
    const validPath = "validpath";
    const invalidPath = "./];";

    const saveNewChunk = async (path) => {
        // enter a new path chunk
        const input = wrapper.find("#path-input-breadcrumb");
        await input.setValue(path);
        expect(input.element.value).toBe(path);

        input.trigger("keyup.enter");
        return input;
    };
    const init = async () => {
        // the file dialog modal should exist
        const filesDialogComponent = wrapper.findComponent(FilesDialog);
        expect(filesDialogComponent.exists()).toBe(true);
        filesDialogComponent.vm.callback({ url: testingData.url });
        // HACK to avoid https://github.com/facebook/jest/issues/2549 (URL implementation is not the same as global node)
        wrapper.vm.pathChunks = testingData.pathChunks;
        await flushPromises();
    };

    beforeEach(async () => {
        spyOnUrlSet = jest.spyOn(FormDirectory.methods, "setUrl");
        spyOnAddPath = jest.spyOn(FormDirectory.methods, "addPath");
        spyOnUpdateURL = jest.spyOn(FormDirectory.methods, "updateURL");

        server.use(
            http.get("/api/remote_files/plugins", ({ response }) => {
                return response(200).json(rootResponse);
            }),

            http.get("/api/configuration", ({ response }) => {
                return response(200).json({});
            })
        );

        const pinia = createPinia();

        wrapper = mount(FormDirectory, {
            propsData: {
                callback: () => {},
            },
            localVue: localVue,
            pinia,
        });
        await flushPromises();
        await init();
    });
    afterEach(async () => {
        if (wrapper) {
            wrapper.destroy();
        }
        wrapper = undefined;
    });

    it("should render Breadcrumb", async () => {
        // after initial folder is chosen, setUrl() should be called and modal disappear
        expect(spyOnUrlSet).toHaveBeenCalled();
        expect(wrapper.findComponent(FilesDialog).exists()).toBe(false);
        expect(wrapper.find("ol.breadcrumb").exists()).toBe(true);

        await flushPromises();

        // check breadcrumb items
        const breadcrumbPaths = wrapper.findAll("li.breadcrumb-item");
        expect(breadcrumbPaths.length).toBe(testingData.expectedNumberOfPaths);
        expect(wrapper.find(".pathname").text()).toBe(testingData.protocol);
        const regularPathElements = wrapper.findAll("li.breadcrumb-item button[disabled='disabled']");

        expect(regularPathElements.length).toBe(testingData.pathChunks.length);

        const chunks = testingData.pathChunks.map((e) => e.pathChunk);
        // every item should be rendered
        for (let i = 0; i < regularPathElements.length; i++) {
            const text = regularPathElements.at(i).text();
            expect(chunks.includes(text)).toBe(true);
        }
    });

    it("should prevent invalid Paths", async () => {
        // enter a new path chunk
        const input = await saveNewChunk(invalidPath);
        await flushPromises();
        // after new entry is entered the value of input should be an empty string
        expect(input.element.value).toBe(invalidPath);
        // should be the same name plus additional item
        expect(wrapper.findAll("li.breadcrumb-item").length).toBe(testingData.expectedNumberOfPaths);
    });

    it("should save and remove new Paths", async () => {
        // enter a new path chunk
        const input = await saveNewChunk(validPath);

        await flushPromises();
        expect(spyOnAddPath).toHaveBeenCalled();
        // after new entry is entered the value of input should be an empty string
        expect(input.element.value).toBe("");

        // should be the same name plus additional item
        expect(wrapper.findAll("li.breadcrumb-item").length).toBe(testingData.expectedNumberOfPaths + 1);
        // find newly added chunk
        const addedChunk = wrapper.findAll("li.breadcrumb-item button").wrappers.find((e) => e.text() === validPath);
        // remove chunk from the path
        await addedChunk.trigger("click");
        await flushPromises();
        // number of elements should be the same again
        expect(wrapper.findAll("li.breadcrumb-item").length).toBe(testingData.expectedNumberOfPaths);
    });

    it("should update new path", async () => {
        // enter a new path chunk
        expect(spyOnUpdateURL).toHaveBeenCalled();
        await saveNewChunk(validPath);
        await flushPromises();

        expect(spyOnUpdateURL).toHaveBeenCalled();
    });
});
