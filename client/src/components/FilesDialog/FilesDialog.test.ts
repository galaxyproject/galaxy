import { composeStories } from "@storybook/vue3-vite";
import { suppressDebugConsole } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { DOMWrapper, VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { SELECTION_STATES, type SelectionItem, type SelectionState } from "@/components/SelectionDialog/selectionTypes";

import * as FilesDialogStories from "./FilesDialog.stories";
import {
    directory1Response,
    directoryId,
    ftpId,
    pdbResponse,
    rootId,
    rootResponse,
    someErrorText,
    subDirectoryId,
    subSubDirectoryId,
} from "./testingData";

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

vi.mock("app");

const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));
vi.mock("@/composables/toast", () => ({
    useToast: () => ({ error: toastError }),
}));

const { server, http } = useServerMock();
const stories = composeStories(FilesDialogStories);
const mountStory = useStoryMount();

interface RowElement extends SelectionItem, Element {
    selectionState: SelectionState;
}

async function waitForIdle(wrapper: VueWrapper<any>) {
    await flushPromises();
    await vi.waitFor(() => expect(wrapper.getComponent(SelectionDialog).props("isBusy")).toBe(false), {
        timeout: 4000,
    });
}

/** Mounts a story and waits for the file sources to load. */
async function initComponent(story: StoryOf<typeof stories>) {
    const wrapper = mountStory(story);
    await waitForIdle(wrapper);
    return wrapper;
}

describe("FilesDialog, file mode", () => {
    let wrapper: VueWrapper<any>;
    let utils: Utils;

    beforeEach(async () => {
        wrapper = await initComponent(stories.MultipleFiles);
        utils = new Utils(wrapper);
    });

    it("should show the number of items expected", async () => {
        await utils.openRootDirectory();
        expect(utils.getRenderedRows().length).toBe(pdbResponse.length);
    });

    it("should list the user defined file sources first", async () => {
        await utils.openRoot();
        const rows = utils.getRenderedRows();
        const firstItem = rows[0];
        expect(firstItem).toBeDefined();
        expect(firstItem!.url).toContain("gxuserfiles://");
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
            expect(item.selectionState).toBe(SELECTION_STATES.SELECTED);
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

        utils.expectSelectAllChecked();
        utils.expectSelectAllNotIndeterminate();

        //every item should be selected
        utils.expectAllRenderedItemsSelected();

        // unselect first file
        const firstFile = utils.findFirstFile();
        await utils.clickOn(firstFile);

        await utils.navigateBack();

        // ensure that it has "mixed" status icon
        const directory = utils.findRenderedDirectory(targetDirectoryId);
        expect(directory.selectionState).toBe(SELECTION_STATES.MIXED);
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
        expect(utils.findRenderedDirectory(subSubDirectoryId).selectionState).toBe(SELECTION_STATES.UNSELECTED);
        // selectAll checkbox should be unchecked
        utils.expectSelectAllUnchecked();
        utils.expectSelectAllNotIndeterminate();
        await utils.navigateBack();
        await utils.navigateBack();
        expect(utils.findRenderedDirectory(directoryId).selectionState).toBe(SELECTION_STATES.MIXED);
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
        expect(rootNode.selectionState).toBe(SELECTION_STATES.SELECTED);
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

        suppressDebugConsole(); // expecting error message.

        // open directory with error
        await utils.openDirectoryById("empty-dir");
        utils.expectErrorMessage();

        // back to the root folder
        await utils.navigateBack();
        expect(utils.getRenderedRows().length).toBe(rootResponse.length);
    });

    it("should show the error and undo the selection when a recursive listing fails", async () => {
        await utils.openRootDirectory();
        server.use(
            http.get("/api/remote_files", ({ response }) => {
                return response("4XX").json({ err_msg: someErrorText, err_code: 400 }, { status: 400 });
            }),
        );

        suppressDebugConsole(); // expecting error message.

        await utils.clickOn(utils.findRenderedDirectory(directoryId));
        expect(toastError).toHaveBeenCalledWith(someErrorText);
        expect(utils.getRenderedRows().length).toBe(pdbResponse.length);
        expect(utils.getSelectionDialog().props("isBusy")).toBe(false);
        utils.expectOkButtonDisabled();
    });
});

describe("FilesDialog, create new file source button", () => {
    let wrapper: VueWrapper<any>;
    let utils: Utils;

    beforeEach(async () => {
        wrapper = await initComponent(stories.SingleFileWithTemplates);
        utils = new Utils(wrapper);
    });
    it("should not render create new button since file source templates are not defined", async () => {
        wrapper = await initComponent(stories.MultipleFiles);
        const createNewButton = wrapper.find("[data-description='create new file source button']");
        expect(createNewButton.exists()).toBe(false);
    });

    it("should render create new button since file source templates are defined and is at root", async () => {
        await utils.openRoot();
        const createNewButton = wrapper.find("[data-description='create new file source button']");
        expect(createNewButton.exists()).toBe(true);
    });

    it("should not render create new button inside folders", async () => {
        await utils.openRootDirectory();
        const createNewButton = wrapper.find("[data-description='create new file source button']");
        expect(createNewButton.exists()).toBe(false);
    });
});

describe("FilesDialog, file mode with templates", () => {
    let wrapper: VueWrapper<any>;
    beforeEach(async () => {
        wrapper = await initComponent(stories.MultipleFilesWithTemplates);
    });
    it("should render create new button since file source templates are defined", async () => {
        const createNewButton = wrapper.find("[data-description='create new file source button']");
        expect(createNewButton.exists()).toBe(true);
    });
});

describe("FilesDialog, file source that cannot list recursively", () => {
    it("should open folders instead of selecting them and select only files", async () => {
        const utils = new Utils(await initComponent(stories.NonRecursiveFileSource));
        await utils.openRootDirectory();

        await utils.clickOn(utils.findRenderedDirectory(directoryId));
        expect(utils.getRenderedRows().map(({ id }) => id)).toEqual(directory1Response.map(({ uri }) => uri));

        const expectOnlyFilesSelected = () =>
            utils.getRenderedRows().forEach((item) => {
                expect(item.selectionState).toBe(item.isLeaf ? SELECTION_STATES.SELECTED : SELECTION_STATES.UNSELECTED);
            });
        await utils.selectAll();
        expectOnlyFilesSelected();

        // one level up, select all first unselects the files picked inside the folder, then selects
        await utils.navigateBack();
        await utils.selectAll();
        utils.getRenderedRows().forEach((item) => expect(item.selectionState).toBe(SELECTION_STATES.UNSELECTED));
        await utils.selectAll();
        expectOnlyFilesSelected();
    });
});

describe("FilesDialog, directory mode", () => {
    let wrapper: VueWrapper<any>;
    let utils: Utils;

    beforeEach(async () => {
        wrapper = await initComponent(stories.Directories);
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
        await utils.openDirectoryById(directoryId);

        utils.expectOkButtonEnabled();
    });

    it("should show loading error and can return back when there is an error", async () => {
        utils.expectNoErrorMessage();

        suppressDebugConsole(); // expecting error message.

        // open directory with error
        await utils.openDirectoryById("empty-dir");
        utils.expectErrorMessage();

        // back to the root folder
        await utils.navigateBack();
        expect(utils.getRenderedRows().length).toBe(rootResponse.length);
    });
});

class Utils {
    wrapper: VueWrapper<any>;

    constructor(wrapper: VueWrapper<any>) {
        this.wrapper = wrapper;
    }

    async openRoot() {
        expect(this.wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        expect(this.getRenderedRows().length).toBe(rootResponse.length);
    }

    async openRootDirectory() {
        await this.openRoot();
        await this.openDirectoryById(rootId);
    }

    async navigateBack() {
        const undoBtn = this.getUndoButton();
        await undoBtn.trigger("click");
        await waitForIdle(this.wrapper);
    }

    async openDirectoryById(directoryId: string) {
        const directory = this.findRenderedDirectory(directoryId);
        return this.openDirectory(directory);
    }

    async openDirectory(directory: RowElement) {
        this.getSelectionDialog().vm.$emit("onOpen", directory);
        await waitForIdle(this.wrapper);
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
            expect(item.selectionState).toBe(SELECTION_STATES.SELECTED);
        });
    }

    expectNumberOfSelectedItemsToBe(number: number) {
        const selectedItems = this.getRenderedRows().filter(
            (item) => item.selectionState === SELECTION_STATES.SELECTED,
        );
        expect(selectedItems.length).toBe(number);
    }

    expectOkButtonDisabled() {
        // GButton uses aria-disabled instead of the native disabled attribute
        expect(this.getOkButton().attributes("aria-disabled")).toBeTruthy();
    }

    expectOkButtonEnabled() {
        expect(this.getOkButton().attributes("aria-disabled")).toBeFalsy();
    }

    getSelectAllCheckbox(): DOMWrapper<HTMLInputElement> {
        const checkbox = this.wrapper.find<HTMLInputElement>("input[id^='g-table-select-all-']");
        expect(checkbox.exists()).toBe(true);
        return checkbox;
    }

    expectSelectAllChecked() {
        const checkbox = this.getSelectAllCheckbox();
        expect((checkbox.element as HTMLInputElement).checked).toBe(true);
    }

    expectSelectAllUnchecked() {
        const checkbox = this.getSelectAllCheckbox();
        expect((checkbox.element as HTMLInputElement).checked).toBe(false);
    }

    expectSelectAllNotIndeterminate() {
        const checkbox = this.getSelectAllCheckbox();
        expect((checkbox.element as HTMLInputElement).indeterminate).toBe(false);
    }

    expectNoErrorMessage() {
        expect(this.wrapper.html()).not.toContain(someErrorText);
    }

    expectErrorMessage() {
        expect(this.wrapper.html()).toContain(someErrorText);
    }
}
