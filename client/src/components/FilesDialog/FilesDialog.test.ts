import { composeStories } from "@storybook/vue3-vite";
import { suppressDebugConsole } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { BrowsableFilesSourcePlugin } from "@/api/remoteFiles";
import { SELECTION_STATES, type SelectionItem, type SelectionState } from "@/components/SelectionDialog/selectionTypes";

import * as FilesDialogStories from "./FilesDialog.stories";
import {
    directory1Response,
    directoryId,
    pdbResponse,
    rdmFileSourceTypes,
    rdmRootId,
    rootId,
    rootResponse,
    someErrorText,
} from "./testingData";

import SelectionDialog from "@/components/SelectionDialog/SelectionDialog.vue";

vi.mock("app");

// Every directory-mode load also lists the RDM sources, which pushes this file past the
// client's per-window request budget and stalls the last tests until the window resets.
vi.mock("@/api/client/rateLimiter", () => ({
    createRateLimiterMiddleware: () => ({ onRequest: ({ request }: { request: Request }) => request }),
}));

const { toastError } = vi.hoisted(() => ({ toastError: vi.fn() }));
vi.mock("@/composables/toast", () => ({ useToast: () => ({ error: toastError }) }));

const { server, http } = useServerMock();

const stories = composeStories(FilesDialogStories);
const mountStory = useStoryMount();

interface RowElement extends SelectionItem, Element {
    selectionState: SelectionState;
}

function getRenderedRows(wrapper: VueWrapper): RowElement[] {
    return wrapper.findComponent(SelectionDialog).props("items") as RowElement[];
}

async function openDirectoryById(wrapper: VueWrapper, id: string) {
    const directory = getRenderedRows(wrapper).find((row) => row.id === id);
    if (!directory) {
        throw new Error(`Directory with id ${id} not found`);
    }
    wrapper.findComponent(SelectionDialog).vm.$emit("onOpen", directory);
    await flushPromises();
    await vi.waitFor(() => expect(wrapper.findComponent(SelectionDialog).props("isBusy")).toBe(false), {
        timeout: 4000,
    });
}

async function navigateBack(wrapper: VueWrapper) {
    await wrapper.find("[data-description='selection dialog undo']").trigger("click");
    await flushPromises();
}

describe("FilesDialog, file mode", () => {
    // The root lists sources without checkboxes, so a source's own selection state isn't shown;
    // the SelectsAll play covers what is.
    it("marks a source selected at the root after selecting all inside it", async () => {
        const wrapper = mountStory(stories.MultipleFiles);
        await flushPromises();
        await openDirectoryById(wrapper, rootId);
        wrapper.findComponent(SelectionDialog).vm.$emit("onSelectAll");
        await flushPromises();
        await openDirectoryById(wrapper, directoryId);
        await navigateBack(wrapper);
        await navigateBack(wrapper);

        const rootNode = getRenderedRows(wrapper).find(({ id }) => id === rootId);
        expect(rootNode?.selectionState).toBe(SELECTION_STATES.SELECTED);
    });
    it("should show the error and undo the selection when a recursive listing fails", async () => {
        const wrapper = mountStory(stories.MultipleFiles);
        await flushPromises();
        await openDirectoryById(wrapper, rootId);
        server.use(
            http.get("/api/remote_files", ({ response }) =>
                response("4XX").json({ err_msg: someErrorText, err_code: 400 }, { status: 400 }),
            ),
        );
        suppressDebugConsole(); // The expected listing failure is logged by the client.
        const dialog = wrapper.findComponent(SelectionDialog);
        const directory = getRenderedRows(wrapper).find(({ id }) => id === directoryId);
        expect(directory).toBeDefined();
        dialog.vm.$emit("onClick", directory);
        await flushPromises();
        await vi.waitFor(() => expect(dialog.props("isBusy")).toBe(false), { timeout: 4000 });
        expect(toastError).toHaveBeenCalledWith(someErrorText);
        expect(getRenderedRows(wrapper)).toHaveLength(pdbResponse.length);
        expect(dialog.props("isBusy")).toBe(false);
        expect(wrapper.get("[data-description='selection dialog ok']").attributes("aria-disabled")).toBe("true");
    });
});

// Keep the upstream nonrecursive-source contract in unit tests until it has a matching play.
describe("FilesDialog, file source that cannot list recursively", () => {
    it("should open folders instead of selecting them and select only files", async () => {
        const wrapper = mountStory(stories.NonRecursiveFileSource);
        await flushPromises();
        await openDirectoryById(wrapper, rootId);
        const dialog = wrapper.findComponent(SelectionDialog);
        const directory = getRenderedRows(wrapper).find(({ id }) => id === directoryId);
        expect(directory).toBeDefined();
        dialog.vm.$emit("onClick", directory);
        await flushPromises();
        expect(getRenderedRows(wrapper).map(({ id }) => id)).toEqual(directory1Response.map(({ uri }) => uri));

        const expectOnlyFilesSelected = () =>
            getRenderedRows(wrapper).forEach((item) => {
                expect(item.selectionState).toBe(item.isLeaf ? SELECTION_STATES.SELECTED : SELECTION_STATES.UNSELECTED);
            });
        const selectAll = async () => {
            dialog.vm.$emit("onSelectAll");
            await flushPromises();
        };
        await selectAll();
        expectOnlyFilesSelected();
        await navigateBack(wrapper);
        await selectAll();
        getRenderedRows(wrapper).forEach((item) => expect(item.selectionState).toBe(SELECTION_STATES.UNSELECTED));
        await selectAll();
        expectOnlyFilesSelected();
    });
});

describe("FilesDialog, directory mode", () => {
    it("should not allow to select the root of a RDM repository added after the dialog was opened", async () => {
        const isRdmFileSource = (fs: BrowsableFilesSourcePlugin) => rdmFileSourceTypes.includes(fs.type);
        const plugins = rootResponse.filter((fs) => !isRdmFileSource(fs));
        const wrapper = mountStory(stories.Directories);
        // registered after the story's handlers so it answers instead of them
        server.use(
            http.get("/api/remote_files/plugins", ({ response, query }) =>
                response(200).json(query.get("include_kind") === "rdm" ? plugins.filter(isRdmFileSource) : plugins),
            ),
        );
        await flushPromises();
        await vi.waitFor(() => expect(wrapper.findComponent(SelectionDialog).props("isBusy")).toBe(false));
        expect(getRenderedRows(wrapper).map(({ id }) => id)).not.toContain(rdmRootId);
        await openDirectoryById(wrapper, rootId);

        plugins.push(...rootResponse.filter(isRdmFileSource));
        await navigateBack(wrapper);
        await vi.waitFor(() => expect(getRenderedRows(wrapper).map(({ id }) => id)).toContain(rdmRootId));
        await openDirectoryById(wrapper, rdmRootId);

        expect(wrapper.get("[data-description='selection dialog ok']").attributes("aria-disabled")).toBe("true");
    });
});
