import { faFileImport, faPlus, faSitemap, faUpload } from "@fortawesome/free-solid-svg-icons";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import { useHistoryStore } from "@/stores/historyStore";

import type { CommandPaletteProvider, PaletteContext, PaletteItem } from "../types";
import { rankPaletteItems } from "../utilities";

interface ActionDefinition extends PaletteItem {
    /** Whether the action is available without a logged-in user */
    anonymous: boolean;
}

const ACTIONS: ActionDefinition[] = [
    {
        id: "actions:upload",
        anonymous: true,
        icon: faUpload,
        keywords: "data import files url paste",
        subtitle: "Upload files from disk, URL or pasted content",
        title: "Upload data",
        handler: () => {
            const { openGlobalUploadModal } = useGlobalUploadModal();
            openGlobalUploadModal();
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
            useHistoryStore().createNewHistory();
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
