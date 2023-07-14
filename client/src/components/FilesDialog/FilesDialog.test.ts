import { createLocalVue, shallowMount, Wrapper } from "@vue/test-utils";
import BootstrapVue, { BButton } from "bootstrap-vue";
import flushPromises from "flush-promises";

import { selectionStates } from "@/components/SelectionDialog/selectionStates";
import { mockFetcher } from "@/schema/__mocks__";

import {
    directory1RecursiveResponse,
    directory1Response,
    directory2RecursiveResponse,
    directoryId,
    ftpId,
    pdbResponse,
    RemoteDirectory,
    RemoteFile,
    RemoteFilesList,
    rootId,
    rootResponse,
    someErrorText,
    subDirectoryId,
    subSubDirectoryId,
    subsubdirectoryResponse,
} from "./testingData";

import FilesDialog from "./FilesDialog.vue";
import DataDialogTable from "@/components/SelectionDialog/DataDialogTable.vue";
import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

jest.mock("app");
jest.mock("@/schema");

interface RemoteFilesParams {
    target: string;
    recursive: boolean;
}

interface RemoteFilesResponse {
    data?: RemoteFilesList;
}

interface RowElement extends Element {
    id: string;
    label: string;
    details: string;
    isLeaf: boolean;
    url: string;
    labelTitle: string;
    _rowVariant: string;
}

function paramsToKey(params: RemoteFilesParams) {
    return JSON.stringify(params);
}

const mockedOkApiRoutesMap = new Map<string, RemoteFilesResponse>([
    [paramsToKey({ target: "gxfiles://pdb-gzip", recursive: false }), { data: pdbResponse }],
    [paramsToKey({ target: "gxfiles://pdb-gzip/directory1", recursive: false }), { data: directory1Response }],
    [paramsToKey({ target: "gxfiles://pdb-gzip/directory1", recursive: true }), { data: directory1RecursiveResponse }],
    [paramsToKey({ target: "gxfiles://pdb-gzip/directory2", recursive: true }), { data: directory2RecursiveResponse }],
    [
        paramsToKey({ target: "gxfiles://pdb-gzip/directory1/subdirectory1", recursive: false }),
        { data: subsubdirectoryResponse },
    ],
]);

const mockedErrorApiRoutesMap = new Map<string, RemoteFilesResponse>([
    [paramsToKey({ target: "gxfiles://empty-dir", recursive: false }), {}],
]);

function getMockResponse(param: RemoteFilesParams) {
    const responseKey = paramsToKey(param);
    if (mockedErrorApiRoutesMap.has(responseKey)) {
        throw Error(someErrorText);
    }
    return mockedOkApiRoutesMap.get(responseKey);
}

const initComponent = async (props: { multiple: boolean; mode?: string }) => {
    const localVue = createLocalVue();

    localVue.use(BootstrapVue);
    localVue.component("BBtnStub", BButton);

    mockFetcher.path("/api/remote_files/plugins").method("get").mock({ data: rootResponse });
    mockFetcher.path("/api/remote_files").method("get").mock(getMockResponse);

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
    let wrapper: Wrapper<any>;
    let utils: Utils;

    beforeEach(async () => {
        wrapper = await initComponent({ multiple: true });
        utils = new Utils(wrapper);
    });

    it("should show the same number of items", async () => {
        await utils.open_root_folder();
        utils.assertShownItems(pdbResponse.length);
    });

    it("select files", async () => {
        const applyForEachFile = (func: { (item: RowElement): void }) => {
            utils.getRenderedFiles().forEach((item: RowElement) => {
                func(item);
            });
        };

        await utils.open_root_folder();
        const files = pdbResponse.filter((item) => item.class === "File");

        // assert that OK button is disabled
        expect(wrapper.vm.hasValue).toBe(false);

        // assert number of rendered files
        utils.assertShownItems(files.length, true);

        // select each rendered file
        applyForEachFile((item: RowElement) => utils.clickOn(item));

        await flushPromises();
        // assert the number of selected files
        expect(wrapper.vm.model.count()).toBe(files.length);

        // assert that re-rendered files are selected
        applyForEachFile((item) => {
            expect(item._rowVariant).toBe(selectionStates.selected);
            wrapper.vm.model.exists(item.id);
        });
        // assert that OK button is active
        expect(wrapper.vm.hasValue).toBe(true);

        // unselect each file
        applyForEachFile((item: RowElement) => utils.clickOn(item));

        // assert that OK button is disabled
        expect(wrapper.vm.hasValue).toBe(false);
    });

    it("select directory", async () => {
        await utils.open_root_folder();

        // select directory
        await utils.clickOn(utils.getRenderedDirectory(directoryId));

        const response_files: RemoteFile[] = [];
        const response_directories: RemoteDirectory[] = [];
        // separate files and directories from response
        directory1RecursiveResponse.forEach((item) => {
            item.class === "File"
                ? response_files.push(item as RemoteFile)
                : response_directories.push(item as RemoteDirectory);
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

        const file = wrapper.vm.items.find((item: RowElement) => item.isLeaf);

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
    let wrapper: Wrapper<any>;
    let utils: Utils;

    beforeEach(async () => {
        wrapper = await initComponent({ multiple: false, mode: "directory" });
        utils = new Utils(wrapper);
    });

    it("should render directories", async () => {
        const assertOnlyDirectoriesRendered = () =>
            wrapper.vm.items.forEach((item: RowElement) => expect(item.isLeaf).toBe(false));

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
    wrapper: Wrapper<any>;

    constructor(wrapper: Wrapper<any>) {
        this.wrapper = wrapper;
    }

    async open_root_folder(isFileMode = true) {
        expect(this.wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        this.assertShownItems(rootResponse.length);
        if (isFileMode) {
            // find desired rootElement
            const rootElement = this.wrapper.vm.items.find((item: RowElement) => rootId === item.id);
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
        this.wrapper.vm.items.forEach((item: RowElement) => {
            // assert style/icon of selected field
            expect(item._rowVariant).toBe(selectionStates.selected);
            // selected items are selected
            expect(
                item.isLeaf
                    ? this.wrapper.vm.model.exists(item.id)
                    : this.wrapper.vm.selectedDirectories.some(({ id }: RowElement) => id === item.id)
            ).toBe(true);
        });
    }

    async openDirectory(directoryId: string) {
        this.getTable().$emit("open", this.getRenderedDirectory(directoryId));
        await flushPromises();
    }

    async clickOn(element: Element) {
        this.getTable().$emit("clicked", element);
        await flushPromises();
    }

    getRenderedDirectory(directoryId: string): RowElement {
        return this.wrapper.vm.items.find(({ id }: RowElement) => directoryId === id);
    }

    getRenderedFiles(): RowElement[] {
        return this.wrapper.vm.items.filter((item: RowElement) => item.isLeaf);
    }

    getTable() {
        return this.wrapper.findComponent(DataDialogTable).vm;
    }

    assertShownItems(length: number, filesOnly = false) {
        const shownItems = filesOnly ? this.getRenderedFiles() : this.wrapper.vm.items;
        expect(shownItems.length).toBe(length);
    }
}
