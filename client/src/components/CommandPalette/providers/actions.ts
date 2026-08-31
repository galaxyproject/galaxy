import { faFileImport, faPlus, faSitemap, faUpload } from "@fortawesome/free-solid-svg-icons";

import { createNewHistory } from "@/api/histories";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import type { CommandPaletteProvider, PaletteContext, PaletteItem } from "../types";
import { rankPaletteItems } from "../utilities";

interface ActionDefinition extends PaletteItem {
    /** Whether the action is available without a logged-in user */
    anonymous: boolean;
}

/** Upload methods, filtered by config and login exactly like the upload panel */
function uploadMethodItems(argQuery: string, ctx: PaletteContext): PaletteItem[] {
    const items = (ctx.uploadMethods ?? [])
        .filter((method) => !method.disabled)
        .map((method) => ({
            id: `actions:upload:${method.id}`,
            icon: method.icon,
            subtitle: method.description,
            title: method.name,
            to: `/upload/${method.id}`,
        }));
    return rankPaletteItems(items, argQuery);
}

async function createNamedHistory(name: string) {
    try {
        // the store's own creation takes no name, so the api call is followed by
        // the same switch it would have done
        const history = await createNewHistory(name);
        await useHistoryStore().setCurrentHistory(history.id);
    } catch (error) {
        Toast.error(errorMessageAsString(error), "Failed to create history");
    }
}

/** Free text action: the typed name is the row enter runs */
function namedHistoryItems(argQuery: string): PaletteItem[] {
    const name = argQuery.trim();
    if (!name) {
        return [];
    }
    return [
        {
            id: "actions:new-history:named",
            icon: faPlus,
            title: `Create history named '${name}'`,
            handler: () => {
                void createNamedHistory(name);
            },
        },
    ];
}

const ACTIONS: ActionDefinition[] = [
    {
        id: "actions:upload",
        anonymous: true,
        icon: faUpload,
        keywords: "data import files url paste",
        subtitle: "Upload files from disk, URL or pasted content",
        title: "Upload data",
        to: "/upload",
        argumentMode: {
            getItems: (argQuery: string, ctx: PaletteContext) => uploadMethodItems(argQuery, ctx),
            label: "pick a method",
            placeholder: "Search upload methods…",
        },
    },
    {
        id: "actions:new-history",
        anonymous: false,
        icon: faPlus,
        keywords: "analysis start fresh",
        subtitle: "Create a new history and switch to it",
        title: "Create new history",
        handler: () => {
            void useHistoryStore().createNewHistory();
        },
        argumentMode: {
            getItems: (argQuery: string) => namedHistoryItems(argQuery),
            label: "name it",
            placeholder: "Name the new history…",
        },
    },
    {
        id: "actions:create-workflow",
        anonymous: false,
        icon: faSitemap,
        keywords: "editor build new",
        subtitle: "Create a new workflow in the editor",
        title: "Create workflow",
        to: "/workflows/create",
    },
    {
        id: "actions:import-workflow",
        anonymous: false,
        icon: faFileImport,
        keywords: "upload trs url file",
        subtitle: "Import a workflow from file, URL or TRS",
        title: "Import workflow",
        to: "/workflows/import",
    },
];

function actionItems(ctx: PaletteContext): PaletteItem[] {
    return ACTIONS.filter((action) => action.anonymous || !ctx.isAnonymous).map(
        ({ anonymous: _anonymous, ...item }) => item,
    );
}

export const actionsProvider: CommandPaletteProvider = {
    id: "actions",
    title: "Actions",
    emptyQueryItems(ctx: PaletteContext) {
        return actionItems(ctx);
    },
    search(query: string, ctx: PaletteContext) {
        return rankPaletteItems(actionItems(ctx), query);
    },
};
