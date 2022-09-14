import FilesDialog from "./FilesDialog";
import SelectionDialog from "components/SelectionDialog/SelectionDialog";
import DataDialogTable from "components/SelectionDialog/DataDialogTable";
import { shallowMount, createLocalVue } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { BButton } from "bootstrap-vue";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";

import {
    ftpId,
    rootId,
    directoryId,
    subDirectoryId,
    subSubDirectoryId,
    rootResponse,
    pdbResponse,
    directory1RecursiveResponse,
    directory2RecursiveResponse,
    directory1Response,
    subsubdirectoryResponse,
    someErrorText,
} from "./testingData";
import { selectionStates } from "components/SelectionDialog/selectionStates";

jest.mock("app");

const api_paths_map = new Map([
    ["/api/remote_files/plugins", rootResponse],
    ["/api/remote_files?target=gxfiles://pdb-gzip", pdbResponse],
    ["/api/remote_files?target=gxfiles://pdb-gzip/directory1", directory1Response],
    ["/api/remote_files?target=gxfiles://pdb-gzip/directory1&recursive=true", directory1RecursiveResponse],
    ["/api/remote_files?target=gxfiles://pdb-gzip/directory2&recursive=true", directory2RecursiveResponse],
    ["/api/remote_files?target=gxfiles://pdb-gzip/directory1/subdirectory1", subsubdirectoryResponse],
]);
const initComponent = async (props, axiosMock) => {
    const localVue = createLocalVue();

    localVue.use(BootstrapVue);
    localVue.component("BBtnStub", BButton);

    // register axios paths
    for (const [path, response] of api_paths_map.entries()) {
        axiosMock.onGet(path).reply(200, response);
    }

    axiosMock.onGet("/api/remote_files?target=gxfiles://empty-dir").reply(404, {
        err_msg: someErrorText,
        err_code: 404,
    });

    const wrapper = shallowMount(FilesDialog, {
        localVue,
        propsData: props,
    });

    await flushPromises();

    return wrapper;
};
// PLEASE NOTE
// during this test we assume this path tree:
// |-- directory1
// |   |-- directory1file1
// |   |-- directory1file2
// |   |-- directory1file3
// |   |-- subdirectory1
// |   |   `-- subsubdirectory
// |   |       `-- subsubfile
// |   `-- subdirectory2
// |       `-- subdirectory2file
// |-- directory2
// |   |-- directory2file1
// |   `-- directory2file2
// |-- file1
// |-- file2

describe("FilesDialog, file mode", () => {
    let wrapper;
    let utils;
    let axiosMock;

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        wrapper = await initComponent({ multiple: true }, axiosMock);
        utils = new Utils(wrapper);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should show the same number of items", async () => {
        await utils.open_root_folder();
        utils.assertShownItems(pdbResponse.length);
    });

    it("select files", async () => {
        const applyForEachFile = (func) => {
            utils.getRenderedFiles().forEach((file) => {
                func(file);
            });
        };

        await utils.open_root_folder();
        const files = pdbResponse.filter((item) => item.class === "File");

        // assert that OK button is disabled
        expect(wrapper.vm.hasValue).toBe(false);

        // assert number of rendered files
        utils.assertShownItems(files.length, true);

        // select each rendered file
        applyForEachFile((file) => utils.clickOn(file));

        await flushPromises();
        // assert the number of selected files
        expect(wrapper.vm.model.count()).toBe(files.length);

        // assert that re-rendered files are selected
        applyForEachFile((file) => {
            expect(file._rowVariant).toBe(selectionStates.selected);
            wrapper.vm.model.exists(file.id);
        });
        // assert that OK button is active
        expect(wrapper.vm.hasValue).toBe(true);

        // unselect each file
        applyForEachFile((file) => utils.clickOn(file));

        // assert that OK button is disabled
        expect(wrapper.vm.hasValue).toBe(false);
    });

    it("select directory", async () => {
        await utils.open_root_folder();

        // select directory
        await utils.clickOn(utils.getRenderedDirectory(directoryId));

        const [response_files, response_directories] = [[], []];
        // separate files and directories from response
        directory1RecursiveResponse.forEach((item) => {
            item.class === "File" ? response_files.push(item) : response_directories.push(item);
        });

        expect(wrapper.vm.model.count()).toBe(response_files.length);

        // +1 because we additionally selected the "directory1" dir
        expect(wrapper.vm.selectedDirectories.length).toBe(response_directories.length + 1);

        // go inside directory1
        await utils.openDirectory(directoryId);

        // select icon button should be active
        expect(wrapper.vm.selectAllIcon).toBe(selectionStates.selected);

        //every item should be selected
        utils.assertAllRenderedItemsSelected();

        const file = wrapper.vm.items.find((item) => item.isLeaf);

        // unlesect random file
        await utils.clickOn(file);

        await utils.navigateBack();
        // ensure that it has "mixed" icon
        expect(utils.getRenderedDirectory(directoryId)._rowVariant).toBe(selectionStates.mixed);
    });

    // Unselect subdirectory1
    it("unselect sub-directory", async () => {
        await utils.open_root_folder();
        // select directory1
        await utils.clickOn(utils.getRenderedDirectory(directoryId));
        //go inside subDirectoryId
        await utils.openDirectory(directoryId);
        await utils.openDirectory(subDirectoryId);
        // unselect subfolder
        await utils.clickOn(utils.getRenderedDirectory(subSubDirectoryId));
        // directory should be unselected
        expect(utils.getRenderedDirectory(subSubDirectoryId)._rowVariant).toBe(selectionStates.unselected);
        // selectAllIcon should be unselected
        expect(wrapper.vm.selectAllIcon).toBe(selectionStates.unselected);
        await utils.navigateBack();
        await utils.navigateBack();
        await flushPromises();
        expect(utils.getRenderedDirectory(directoryId)._rowVariant).toBe(selectionStates.mixed);
    });

    it("should select all on 'toggleSelectAll' event", async () => {
        await utils.open_root_folder();
        // selectAll button was pressed
        utils.getTable().$emit("toggleSelectAll");
        await flushPromises();
        utils.assertAllRenderedItemsSelected();
        // open directory1
        await utils.openDirectory(directoryId);
        utils.assertAllRenderedItemsSelected();
        await utils.navigateBack();
        utils.assertAllRenderedItemsSelected();
        await utils.navigateBack();
        const rootNode = utils.getRenderedDirectory(rootId);
        expect(rootNode._rowVariant).toBe(selectionStates.selected);
    });

    it("should show ftp helper only in ftp directory", async () => {
        // open some other directory than ftp
        await utils.open_root_folder();
        // check that ftp helper is not visible
        expect(wrapper.vm.showFTPHelper).toBe(false);
        expect(wrapper.find("#helper").exists()).toBe(false);
        // back to root folder
        await utils.navigateBack();

        // open ftp directory
        await utils.openDirectory(ftpId);
        // check that ftp helper is visible
        expect(wrapper.vm.showFTPHelper).toBe(true);
        expect(wrapper.find("#helper").exists()).toBe(true);
    });

    it("should show loading error and can return back", async () => {
        expect(wrapper.vm.errorMessage).toBeNull();

        // open directory with error
        await utils.openDirectory("empty-dir");
        // assert that error message is set and showed
        expect(wrapper.vm.errorMessage).toBe(someErrorText);
        expect(wrapper.html()).toContain(someErrorText);

        // assert that OK button is disabled
        expect(wrapper.vm.hasValue).toBe(false);

        // back to the root folder
        await wrapper.find("#back-btn").trigger("click");
        await flushPromises();
        expect(wrapper.vm.items.length).toBe(rootResponse.length);

        // assert that OK button is disabled
        expect(wrapper.vm.hasValue).toBe(false);
    });
});

describe("FilesDialog, directory mode", () => {
    let wrapper;
    let utils;
    let axiosMock;

    const spyFinalize = jest.spyOn(FilesDialog.methods, "finalize");

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);
        wrapper = await initComponent({ multiple: false, mode: "directory" }, axiosMock);
        utils = new Utils(wrapper);
    });

    afterEach(() => {
        axiosMock.restore();
    });

    it("should render directories", async () => {
        const assertOnlyDirectoriesRendered = () => wrapper.vm.items.forEach((item) => expect(item.isLeaf).toBe(false));

        await utils.open_root_folder(false);
        // rendered files should be directories
        assertOnlyDirectoriesRendered();
        // check subdirectories
        await utils.openDirectory(directoryId);
        assertOnlyDirectoriesRendered();
    });

    it("should select folders", async () => {
        const btn = wrapper.find("#ok-btn");

        expect(btn.attributes().disabled).toBe("disabled");
        await utils.open_root_folder(false);
        const folder = utils.getRenderedDirectory(directoryId);
        await utils.getTable().$emit("open", folder);
        await flushPromises();

        const currentDirectory = wrapper.vm.currentDirectory;
        expect(currentDirectory.id).toBe(folder.id);

        // make sure that disabled attribute is absent
        expect(btn.attributes().disabled).toBe(undefined);
        wrapper.vm.selectLeaf(currentDirectory);
        await flushPromises();

        // finalize function should be called
        expect(spyFinalize).toHaveBeenCalled();
        //should close modal
        expect(wrapper.vm.modalShow).toBe(false);
    });

    it("should show loading error and can return back", async () => {
        expect(wrapper.vm.errorMessage).toBeNull();

        // open directory with error
        await utils.openDirectory("empty-dir");
        // assert that error message is set and showed
        expect(wrapper.vm.errorMessage).toBe(someErrorText);
        expect(wrapper.html()).toContain(someErrorText);

        // assert that OK button is disabled
        expect(wrapper.vm.hasValue).toBe(false);

        // back to the root folder
        await wrapper.find("#back-btn").trigger("click");
        await flushPromises();
        expect(wrapper.vm.items.length).toBe(rootResponse.length);

        // assert that OK button is disabled
        expect(wrapper.vm.hasValue).toBe(false);
    });
});

/** Util methods **/
class Utils {
    constructor(wrapper) {
        this.wrapper = wrapper;
    }

    async open_root_folder(isFileMode = true) {
        expect(this.wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        this.assertShownItems(rootResponse.length);
        if (isFileMode) {
            // find desired rootElement
            const rootElement = this.wrapper.vm.items.find((item) => rootId === item.id);
            // open root folder with rootId (since root folder cannot be selected "click" should open it)
            await this.clickOn(rootElement);
        } else {
            await this.openDirectory(rootId);
        }
    }

    async navigateBack() {
        this.wrapper.vm.load();
        await flushPromises();
    }

    assertAllRenderedItemsSelected() {
        this.wrapper.vm.items.forEach((item) => {
            // assert style/icon of selected field
            expect(item._rowVariant).toBe(selectionStates.selected);
            // selected items are selected
            expect(
                item.isLeaf
                    ? this.wrapper.vm.model.exists(item.id)
                    : this.wrapper.vm.selectedDirectories.some(({ id }) => id === item.id)
            ).toBe(true);
        });
    }

    async openDirectory(directoryId) {
        this.getTable().$emit("open", this.getRenderedDirectory(directoryId));
        await flushPromises();
    }

    async clickOn(element) {
        this.getTable().$emit("clicked", element);
        await flushPromises();
    }

    getRenderedDirectory(directoryId) {
        return this.wrapper.vm.items.find(({ id }) => directoryId === id);
    }

    getRenderedFiles() {
        return this.wrapper.vm.items.filter((item) => item.isLeaf);
    }

    getTable() {
        return this.wrapper.findComponent(DataDialogTable).vm;
    }

    assertShownItems(length, filesOnly) {
        const shownItems = filesOnly ? this.getRenderedFiles() : this.wrapper.vm.items;
        expect(shownItems.length).toBe(length);
    }
}
