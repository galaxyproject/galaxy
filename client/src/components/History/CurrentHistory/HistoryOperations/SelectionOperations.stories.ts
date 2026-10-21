import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withLoadedConfig } from "@tests/test-data/config";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { expect, waitFor, within } from "storybook/test";

import { configurationHandler, http } from "@/api/client/__mocks__/http";
import { selectableObjectStores } from "@/components/ObjectStore/test_fixtures";

import {
    DELETED_DATASET,
    HIDDEN_DATASET,
    HISTORY,
    PURGED_DATASET,
    READS_COLLECTION,
    selectionOf,
    VISIBLE_DATASET,
} from "./test_fixtures";

import SelectionOperations from "./SelectionOperations.vue";

/**
 * The "Selection" menu above a history's items, once some are selected, on a Galaxy that runs
 * background tasks, so the data type and storage operations are offered.
 */
const meta = {
    title: "History/CurrentHistory/HistoryOperations/SelectionOperations",
    component: SelectionOperations,
    // The data type item follows the configuration, so a missing one is really missing.
    decorators: [withLoadedConfig, withCurrentUser()],
    args: {
        history: HISTORY,
        filterText: "",
        contentSelection: selectionOf(VISIBLE_DATASET),
        selectionSize: 1,
        isQuerySelection: false,
        isMultiViewItem: false,
        totalItemsInQuery: HISTORY.count,
    },
    argTypes: { contentSelection: { control: false } },
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler({ enable_celery_tasks: true }),
                objectStores: selectableObjectStores(),
                // The Database/Build dialog lists them when it opens.
                genomes: http.get("/api/genomes", ({ response }) => response(200).json([])),
            },
        },
    },
} satisfies Meta<typeof SelectionOperations>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

const STORAGE = "Manage Storage Location";
/** The items that don't depend on the selection, with Celery. */
const COMMON_ITEMS = ["Change Database/Build", "Change data type", "Add tags", "Remove tags", STORAGE];

/** Opens the "Selection" menu from its `toggle` button and returns the open menu. */
async function openSelectionMenu({ canvas, step, userEvent }: PlayContext, toggle: string) {
    let menu!: HTMLElement;
    await step(`Open the "${toggle}" menu`, async () => {
        const button = await canvas.findByRole("button", { name: toggle }, { timeout: 5000 });
        await expect(canvas.queryByRole("menu")).not.toBeInTheDocument();
        await userEvent.click(button);
        menu = await canvas.findByRole("menu", { name: toggle });
        await expect(menu).toBeVisible();
    });
    return menu;
}

/**
 * Opens the "Selection" menu, reads its count and its items in order, and closes it again, so the
 * story still shows its initial state. `alsoAccepted` lists other item lists a known bug allows.
 */
function offersSelectionMenu(toggle: string, count: number, items: string[], alsoAccepted: string[][] = []) {
    return async (context: PlayContext) => {
        const { canvas, step, userEvent } = context;
        const menu = await openSelectionMenu(context, toggle);
        await step(`Read "With ${count} selected..." and the items: ${items.join(", ")}`, async () => {
            await expect(within(menu).getByText(`With ${count} selected...`)).toBeVisible();
            if (items.includes(STORAGE)) {
                // It waits for the storage locations to load.
                await within(menu).findByRole("menuitem", { name: STORAGE }, { timeout: 5000 });
            }
            const names = within(menu)
                .getAllByRole("menuitem")
                .map((item) => item.textContent?.trim());
            await expect([items, ...alsoAccepted]).toContainEqual(names);
        });
        await step("Close the menu", async () => {
            await userEvent.click(canvas.getByRole("button", { name: toggle }));
            await waitFor(() => expect(canvas.queryByRole("menu")).not.toBeInTheDocument());
        });
    };
}

/**
 * Offers `items` for a selection of active datasets. The Undelete item ignores whether the selected
 * items are deleted, so a filter that doesn't pin `deleted` offers it for them too; accepts that.
 */
function offersForActiveDatasets(toggle: string, count: number, items: string[]) {
    const withUndelete = [...items];
    withUndelete.splice(items.indexOf("Delete"), 0, "Undelete");
    return offersSelectionMenu(toggle, count, items, [withUndelete]);
}

/** One visible dataset selected under the default filter. */
export const DatasetSelected: Story = {
    play: offersSelectionMenu("1 of 5 selected", 1, [
        "Hide",
        "Delete",
        "Delete (permanently)",
        ...COMMON_ITEMS,
        "Auto Build List",
        "Advanced Build List",
    ]),
};

/** Showing hidden items only, with a hidden dataset selected: it can be unhidden. */
export const HiddenSelected: Story = {
    args: { filterText: "visible:false", contentSelection: selectionOf(HIDDEN_DATASET) },
    play: offersForActiveDatasets("1 of 5 selected", 1, ["Unhide", "Delete", "Delete (permanently)", ...COMMON_ITEMS]),
};

/** Showing visible and hidden items, with one of each selected: both hide and unhide apply. */
export const VisibleAndHiddenSelected: Story = {
    args: {
        filterText: "visible:any",
        contentSelection: selectionOf(VISIBLE_DATASET, HIDDEN_DATASET),
        selectionSize: 2,
    },
    play: offersForActiveDatasets("2 of 5 selected", 2, [
        "Unhide",
        "Hide",
        "Delete",
        "Delete (permanently)",
        ...COMMON_ITEMS,
    ]),
};

/** Showing deleted items only, with a deleted dataset selected: it can be undeleted. */
export const DeletedSelected: Story = {
    args: { filterText: "deleted:true", contentSelection: selectionOf(DELETED_DATASET) },
    play: offersSelectionMenu("1 of 5 selected", 1, ["Hide", "Undelete", "Delete (permanently)", ...COMMON_ITEMS]),
};

/** Showing active and deleted items, with one of each selected: both delete and undelete apply. */
export const ActiveAndDeletedSelected: Story = {
    args: {
        filterText: "deleted:any",
        contentSelection: selectionOf(VISIBLE_DATASET, DELETED_DATASET),
        selectionSize: 2,
    },
    play: offersSelectionMenu("2 of 5 selected", 2, [
        "Hide",
        "Undelete",
        "Delete",
        "Delete (permanently)",
        ...COMMON_ITEMS,
    ]),
};

/** Showing active and deleted items, with an active collection selected: it can be deleted, not undeleted. */
export const ActiveCollectionSelected: Story = {
    args: { filterText: "deleted:any", contentSelection: selectionOf(READS_COLLECTION) },
    // Collections carry no `purged` flag, and the menu counts an item without one as purged, so it
    // doesn't offer to delete a collection permanently. Accepts the list with that item too.
    play: offersSelectionMenu(
        "1 of 5 selected",
        1,
        ["Hide", "Delete", ...COMMON_ITEMS],
        [["Hide", "Delete", "Delete (permanently)", ...COMMON_ITEMS]],
    ),
};

/** Showing deleted items only, with a purged dataset selected: it can't be undeleted or purged again. */
export const PurgedSelected: Story = {
    args: { filterText: "deleted:true", contentSelection: selectionOf(PURGED_DATASET) },
    play: offersSelectionMenu("1 of 5 selected", 1, ["Hide", ...COMMON_ITEMS]),
};

/** Every item the filter matches is selected, so the menu offers a list built from all of them. */
export const WholeQuerySelected: Story = {
    args: { history: { ...HISTORY, count: 105 }, selectionSize: 105, totalItemsInQuery: 105, isQuerySelection: true },
    play: offersSelectionMenu("All 105 selected", 105, [
        "Hide",
        "Delete",
        "Delete (permanently)",
        "Build Dataset List",
        ...COMMON_ITEMS,
    ]),
};

/** A Galaxy without background tasks: no data type or storage operations. */
export const WithoutCelery: Story = {
    parameters: { msw: { handlers: { configuration: configurationHandler({ enable_celery_tasks: false }) } } },
    play: offersSelectionMenu("1 of 5 selected", 1, [
        "Hide",
        "Delete",
        "Delete (permanently)",
        "Change Database/Build",
        "Add tags",
        "Remove tags",
        "Auto Build List",
        "Advanced Build List",
    ]),
};

/** Opens the `menuItem` tag dialog and its tag editor: the suggestions show in the dialog body, above Cancel and Ok. */
function showsTagSuggestions(menuItem: string, heading: string, prompt: string) {
    return async (context: PlayContext) => {
        const { step, userEvent } = context;
        const menu = await openSelectionMenu(context, "1 of 5 selected");
        let dialog!: HTMLElement;
        await step(`Choose "${menuItem}": the "${heading}" dialog opens`, async () => {
            await userEvent.click(within(menu).getByRole("menuitem", { name: menuItem }));
            dialog = await within(document.body).findByRole("dialog");
            await expect(within(dialog).getByRole("heading", { name: heading })).toBeVisible();
            await expect(within(dialog).getByText(prompt)).toBeVisible();
            await expect(within(dialog).queryByRole("listbox")).not.toBeInTheDocument();
        });
        await step("Open the tag editor and type a tag: its suggestion shows above Cancel and Ok", async () => {
            await userEvent.click(within(dialog).getByRole("button", { name: "Add Tags" }));
            await userEvent.keyboard("rnaseq");
            const listbox = await within(dialog).findByRole("listbox");
            await expect(within(listbox).getByRole("option", { name: /rnaseq/ })).toBeVisible();
            // In the dialog body: after its prompt, before its tip and buttons.
            const following = [
                within(dialog).getByText("Press Enter after typing each tag."),
                within(dialog).getByRole("button", { name: "Cancel" }),
                within(dialog).getByRole("button", { name: "Ok" }),
            ];
            await expect(
                within(dialog).getByText(prompt).compareDocumentPosition(listbox) & Node.DOCUMENT_POSITION_FOLLOWING,
            ).toBeTruthy();
            for (const element of following) {
                await expect(listbox.compareDocumentPosition(element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
            }
        });
    };
}

/** "Add tags" opens a dialog that lists its tag suggestions in its body, before Cancel and Ok. */
export const SuggestsTagsToAdd: Story = {
    play: showsTagSuggestions("Add tags", "Add tags?", "Apply the following tags to 1 items:"),
};

/** "Remove tags" opens a dialog that lists its tag suggestions in its body, before Cancel and Ok. */
export const SuggestsTagsToRemove: Story = {
    play: showsTagSuggestions("Remove tags", "Remove tags?", "Remove the following tags from 1 items:"),
};
