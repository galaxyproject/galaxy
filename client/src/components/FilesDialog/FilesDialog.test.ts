import { createTestingPinia } from "@pinia/testing";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { SELECTION_STATES, type SelectionItem } from "@/components/SelectionDialog/selectionTypes";

/**
 * The following imports mock a remote file resource directory structure,
 * which is navigated throughout the test cases further below.
 * The directory tree path is as follows:
 *
 * |-- directory1
 * |   |-- directory1file1
 * |   |-- directory1file2
 * |   |-- directory1file3
 * |   |-- subdirectory1
 * |   |   `-- subsubdirectory
 * |   |       `-- subsubfile
 * |   `-- subdirectory2
 * |       `-- subdirectory2file
 * |-- directory2
 * |   |-- directory2file1
 * |   `-- directory2file2
 * |-- file1
 * |-- file2
 */
import { type RemoteFilesList } from "./testingData";
import {
    directory1RecursiveResponse,
    directory1Response,
    directory2RecursiveResponse,
    directoryId,
    ftpId,
    pdbResponse,
    rootId,
    rootResponse,
    someErrorText,
    subDirectoryId,
    subSubDirectoryId,
    subsubdirectoryResponse,
} from "./testingData";

import FilesDialog from "./FilesDialog.vue";
import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

jest.mock("app");

jest.mock("@/composables/config", () => ({
    useConfig: jest.fn(() => ({
        config: { ftp_upload_site: "Test ftp upload site" },
        isConfigLoaded: true,
    })),
}));

const { server, http } = useServerMock();

interface RowElement extends SelectionItem, Element {
    _rowVariant: string;
}

function paramsToKey(query: { target?: string | null; recursive?: string | null; writeable?: string | null }): string {
    return `${query.target}?recursive=${query.recursive}&writeable=${query.writeable ?? "false"}`;
}

const mockedOkApiRoutesMap = new Map<string, RemoteFilesList>([
    [paramsToKey({ target: "gxfiles://pdb-gzip", recursive: "false" }), pdbResponse],
    [paramsToKey({ target: "gxfiles://pdb-gzip/directory1", recursive: "false" }), directory1Response],
    [paramsToKey({ target: "gxfiles://pdb-gzip/directory1", recursive: "true" }), directory1RecursiveResponse],
    [paramsToKey({ target: "gxfiles://pdb-gzip/directory2", recursive: "true" }), directory2RecursiveResponse],
    [
        paramsToKey({ target: "gxfiles://pdb-gzip/directory1/subdirectory1", recursive: "false" }),
        subsubdirectoryResponse,
    ],
]);

const mockedErrorApiRoutesMap = new Map<string, RemoteFilesList>([
    [paramsToKey({ target: "gxfiles://empty-dir", recursive: "false" }), []],
]);

const initComponent = async (props: { multiple: boolean; mode?: string }) => {
    const localVue = getLocalVue();

    server.use(
        http.get("/api/remote_files/plugins", ({ response }) => {
            return response(200).json(rootResponse);
        }),

        http.get("/api/remote_files", ({ response, query }) => {
            const responseKey = paramsToKey({
                target: query.get("target"),
                recursive: query.get("recursive"),
                writeable: query.get("writeable"),
            });
            if (mockedErrorApiRoutesMap.has(responseKey)) {
                return response("4XX").json({ err_msg: someErrorText, err_code: 400 }, { status: 400 });
            }
            const mockedResponse = mockedOkApiRoutesMap.get(responseKey);
            const mockedTotalMatches = mockedResponse?.length.toString() ?? "0";
            if (!mockedResponse) {
                return response("5XX").json({ err_msg: "No mocked response found", err_code: 500 }, { status: 500 });
            }
            return response(200).json(mockedResponse, { headers: { total_matches: mockedTotalMatches } });
        })
    );

    const testingPinia = createTestingPinia({ stubActions: false });
    const wrapper = mount(FilesDialog, {
        localVue,
        propsData: { ...props, modalStatic: true },
        pinia: testingPinia,
    });

    await flushPromises();
    return wrapper;
};

describe("FilesDialog, file mode", () => {
    let wrapper: Wrapper<any>;
    let utils: Utils;

    beforeEach(async () => {
        wrapper = await initComponent({ multiple: true });
        utils = new Utils(wrapper);
    });

    it("should show the number of items expected", async () => {
        await utils.openRootDirectory();
        expect(utils.getRenderedRows().length).toBe(pdbResponse.length);
    });

    it("should allow selecting files and update OK button accordingly", async () => {
        await utils.openRootDirectory();
        const filesInResponse = pdbResponse.filter((item) => item.class === "File");

        utils.expectOkButtonDisabled();

        expect(utils.getRenderedFiles().length).toBe(filesInResponse.length);

        // select each file
        await utils.applyToEachFile((item) => utils.clickOn(item));

        utils.expectNumberOfSelectedItemsToBe(filesInResponse.length);

        await utils.applyToEachFile((item) => {
            expect(item._rowVariant).toBe(SELECTION_STATES.SELECTED);
        });

        utils.expectOkButtonEnabled();

        // unselect each file
        await utils.applyToEachFile((item) => utils.clickOn(item));

        utils.expectOkButtonDisabled();
    });

    it("should select all files contained in a directory when selecting the directory and update selection status accordingly", async () => {
        const targetDirectoryId = directoryId;
        await utils.openRootDirectory();

        // select directory
        await utils.clickOn(utils.findRenderedDirectory(targetDirectoryId));

        // go inside directory1
        await utils.openDirectoryById(targetDirectoryId);

        utils.expectSelectAllIconStatusToBe(SELECTION_STATES.SELECTED);

        //every item should be selected
        utils.expectAllRenderedItemsSelected();

        // unselect first file
        const firstFile = utils.findFirstFile();
        await utils.clickOn(firstFile);

        await utils.navigateBack();

        // ensure that it has "mixed" status icon
        const directory = utils.findRenderedDirectory(targetDirectoryId);
        expect(directory._rowVariant).toBe(SELECTION_STATES.MIXED);
    });

    it("should be able to unselect a sub-directory keeping the rest selected", async () => {
        await utils.openRootDirectory();
        // select directory1
        await utils.clickOn(utils.findRenderedDirectory(directoryId));
        //go inside subDirectoryId
        await utils.openDirectoryById(directoryId);
        await utils.openDirectoryById(subDirectoryId);
        // unselect subfolder
        await utils.clickOn(utils.findRenderedDirectory(subSubDirectoryId));
        // directory should be unselected
        expect(utils.findRenderedDirectory(subSubDirectoryId)._rowVariant).toBe(SELECTION_STATES.UNSELECTED);
        // selectAllIcon should be unselected
        utils.expectSelectAllIconStatusToBe(SELECTION_STATES.UNSELECTED);
        await utils.navigateBack();
        await utils.navigateBack();
        expect(utils.findRenderedDirectory(directoryId)._rowVariant).toBe(SELECTION_STATES.MIXED);
    });

    it("should select all on 'toggleSelectAll' event", async () => {
        await utils.openRootDirectory();
        utils.selectAll();
        utils.expectAllRenderedItemsSelected();
        // open directory1
        await utils.openDirectoryById(directoryId);
        utils.expectAllRenderedItemsSelected();
        await utils.navigateBack();
        utils.expectAllRenderedItemsSelected();
        await utils.navigateBack();
        const rootNode = utils.findRenderedDirectory(rootId);
        expect(rootNode._rowVariant).toBe(SELECTION_STATES.SELECTED);
    });

    it("should show ftp helper only in ftp directory", async () => {
        // open some other directory than ftp
        await utils.openRootDirectory();
        // check that ftp helper is not visible
        expect(wrapper.find("#helper").exists()).toBe(false);

        // back to root folder
        await utils.navigateBack();

        // open ftp directory
        await utils.openDirectoryById(ftpId);
        // check that ftp helper is visible
        expect(wrapper.find("#helper").exists()).toBe(true);
    });

    it("should show loading error and can return back when there is an error", async () => {
        utils.expectNoErrorMessage();

        // open directory with error
        await utils.openDirectoryById("empty-dir");
        utils.expectErrorMessage();

        // back to the root folder
        await utils.navigateBack();
        expect(utils.getRenderedRows().length).toBe(rootResponse.length);
    });
});

describe("FilesDialog, directory mode", () => {
    let wrapper: Wrapper<any>;
    let utils: Utils;

    beforeEach(async () => {
        wrapper = await initComponent({ multiple: false, mode: "directory" });
        utils = new Utils(wrapper);
    });

    it("should render directories only", async () => {
        const expectOnlyDirectoriesRendered = () =>
            utils.getRenderedRows().forEach((item) => expect(item.isLeaf).toBe(false));

        await utils.openRootDirectory();
        // rendered files should be directories
        expectOnlyDirectoriesRendered();
        // check subdirectories
        await utils.openDirectoryById(directoryId);
        expectOnlyDirectoriesRendered();
    });

    it("should allow to select folders by navigating to them", async () => {
        utils.expectOkButtonDisabled();

        await utils.openRootDirectory();
        utils.openDirectoryById(directoryId);

        utils.expectOkButtonEnabled();
    });

    it("should show loading error and can return back when there is an error", async () => {
        utils.expectNoErrorMessage();

        // open directory with error
        await utils.openDirectoryById("empty-dir");
        utils.expectErrorMessage();

        // back to the root folder
        await utils.navigateBack();
        expect(utils.getRenderedRows().length).toBe(rootResponse.length);
    });
});

class Utils {
    wrapper: Wrapper<any>;

    constructor(wrapper: Wrapper<any>) {
        this.wrapper = wrapper;
    }

    async openRootDirectory() {
        expect(this.wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        expect(this.getRenderedRows().length).toBe(rootResponse.length);
        await this.openDirectoryById(rootId);
    }

    async navigateBack() {
        const undoBtn = this.getUndoButton();
        await undoBtn.trigger("click");
        await flushPromises();
    }

    async openDirectoryById(directoryId: string) {
        const directory = this.findRenderedDirectory(directoryId);
        return this.openDirectory(directory);
    }

    async openDirectory(directory: RowElement) {
        this.getSelectionDialog().vm.$emit("onOpen", directory);
        await flushPromises();
    }

    async clickOn(element: Element) {
        this.getSelectionDialog().vm.$emit("onClick", element);
        await flushPromises();
    }

    async selectAll() {
        this.getSelectionDialog().vm.$emit("onSelectAll");
        await flushPromises();
    }

    findRenderedDirectory(directoryId: string): RowElement {
        const directory = this.getRenderedRows().find(({ id }: RowElement) => directoryId === id);
        if (!directory) {
            throw new Error(`Directory with id ${directoryId} not found`);
        }
        return directory;
    }

    getRenderedFiles(): RowElement[] {
        return this.getRenderedRows().filter((item: RowElement) => item.isLeaf);
    }

    findFirstFile(): RowElement {
        const file = this.getRenderedFiles()[0];
        if (!file) {
            throw new Error("File not found");
        }
        return file;
    }

    async applyToEachFile(func: (item: RowElement) => void) {
        this.getRenderedFiles().forEach((item) => {
            func(item);
        });
        await flushPromises();
    }

    getSelectionDialog(): any {
        return this.wrapper.findComponent(SelectionDialog);
    }

    getButtonById(id: string): any {
        const button = this.wrapper.find(`[data-description='selection dialog ${id}']`);
        expect(button.exists()).toBe(true);
        return button;
    }

    getOkButton(): any {
        return this.getButtonById("ok");
    }

    getUndoButton(): any {
        return this.getButtonById("undo");
    }

    getRenderedRows(): RowElement[] {
        return this.getSelectionDialog().props("items") as RowElement[];
    }

    expectAllRenderedItemsSelected() {
        this.getRenderedRows().forEach((item) => {
            expect(item._rowVariant).toBe(SELECTION_STATES.SELECTED);
        });
    }

    expectNumberOfSelectedItemsToBe(number: number) {
        const selectedItems = this.getRenderedRows().filter((item) => item._rowVariant === SELECTION_STATES.SELECTED);
        expect(selectedItems.length).toBe(number);
    }

    expectOkButtonDisabled() {
        expect(this.getOkButton().attributes("disabled")).toBeTruthy();
    }

    expectOkButtonEnabled() {
        expect(this.getOkButton().attributes("disabled")).toBeFalsy();
    }

    expectSelectAllIconStatusToBe(status: string) {
        expect(this.getSelectionDialog().props("selectAllIcon")).toBe(status);
    }

    expectNoErrorMessage() {
        expect(this.wrapper.html()).not.toContain(someErrorText);
    }

    expectErrorMessage() {
        expect(this.wrapper.html()).toContain(someErrorText);
    }
}
