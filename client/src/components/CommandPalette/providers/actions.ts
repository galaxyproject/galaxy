import {
    faComments,
    faFileAlt,
    faFileImport,
    faMagic,
    faPlay,
    faPlus,
    faSitemap,
    faUpload,
} from "@fortawesome/free-solid-svg-icons";

import { createNewHistory } from "@/api/histories";
import { createPage } from "@/api/pages";
import { Toast } from "@/composables/toast";
import { useChatStore } from "@/stores/chatStore";
import { useHistoryStore } from "@/stores/historyStore";
import { usePageStore } from "@/stores/pageStore";
import { errorMessageAsString } from "@/utils/simple-error";

import type { CommandPaletteProvider, PaletteContext, PaletteItem } from "../types";
import { rankPaletteItems } from "../utilities";
import { myWorkflowItems } from "./workflows";

interface ActionDefinition extends PaletteItem {
    /** Whether the action is available without a logged-in user */
    anonymous: boolean;
    /** Extra availability check against the Galaxy configuration */
    configGate?: (ctx: PaletteContext) => boolean;
}

/** Per argument section cap, matching the scoped providers */
const ARGUMENT_LIMIT = 8;

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
    const historyStore = useHistoryStore();
    try {
        // the store's own creation takes no name, so the api call is followed by
        // the same switch it would have done
        const history = await createNewHistory(name);
        await historyStore.setCurrentHistory(history.id);
    } catch (error) {
        Toast.error(errorMessageAsString(error), "Failed to create history");
        return;
    }
    try {
        // the history exists either way: keep the store's paginated total and
        // offset in step with it, exactly like `historyStore.createNewHistory`
        await historyStore.handleTotalCountChange(1);
    } catch (error) {
        // a stale count is not worth reporting as a failed creation
        console.debug("Command palette could not refresh the history count", error);
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

/**
 * Page identifier the backend accepts: lowercase, every run of other characters
 * turned into a single dash, no dash at either end.
 */
export function slugify(title: string): string {
    const slug = title
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "");
    // a title made of punctuation alone would leave nothing to send
    return slug || "page";
}

/** The backend rejects a slug that the user already has with this message */
function isSlugConflict(error: unknown): boolean {
    return /must be unique/i.test(String(errorMessageAsString(error, "")));
}

async function createTitledPage(title: string, ctx: PaletteContext) {
    const slug = slugify(title);
    try {
        let page;
        try {
            page = await createPage({ title, slug, content_format: "markdown" });
        } catch (error) {
            if (!isSlugConflict(error)) {
                throw error;
            }
            // one retry is enough: the suffixed slug is free unless the user
            // already owns both, which is worth reporting
            page = await createPage({ title, slug: `${slug}-2`, content_format: "markdown" });
        }
        // the `p:` scope renders from the store and stops asking the backend once
        // it holds every page, so the new one has to be seeded or it stays hidden
        usePageStore().savePages("my", [page], true);
        ctx.navigate?.(`/pages/editor?id=${page.id}`);
    } catch (error) {
        Toast.error(errorMessageAsString(error), "Failed to create page");
    }
}

/** Free text action: the typed title is the row enter runs */
function titledPageItems(argQuery: string): PaletteItem[] {
    const title = argQuery.trim();
    if (!title) {
        return [];
    }
    return [
        {
            id: "actions:create-page:titled",
            icon: faFileAlt,
            title: `Create page titled '${title}'`,
            handler: (ctx: PaletteContext) => {
                void createTitledPage(title, ctx);
            },
        },
    ];
}

/**
 * GalaxyAI rows: the typed question seeds a fresh conversation through
 * `/galaxyai/new?q=`, the existing conversations open where they left off.
 */
async function galaxyAiItems(argQuery: string): Promise<PaletteItem[]> {
    const chatStore = useChatStore();
    const question = argQuery.trim();
    if (chatStore.chatHistory.length === 0 && !chatStore.loading) {
        try {
            await chatStore.loadHistory();
        } catch (error) {
            console.debug("Command palette could not load the GalaxyAI history", error);
        }
    }
    const existing = chatStore.chatHistory.map((chat) => ({
        id: `actions:galaxy-ai:${chat.id}`,
        icon: faComments,
        title: chat.query || "Untitled conversation",
        subtitle: chat.response,
        to: `/galaxyai/${chat.id}`,
    }));
    const seeded = question
        ? [
              {
                  id: "actions:galaxy-ai:new",
                  icon: faMagic,
                  title: `New chat: '${question}'`,
                  to: `/galaxyai/new?q=${encodeURIComponent(question)}`,
              },
          ]
        : [];
    return [...seeded, ...rankPaletteItems(existing, question).slice(0, ARGUMENT_LIMIT)];
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
            emptyHint: "Type a name for the new history…",
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
    {
        id: "actions:create-page",
        anonymous: false,
        icon: faFileAlt,
        keywords: "markdown document report notebook new",
        subtitle: "Create a new page and open the editor",
        title: "Create new page",
        to: "/pages/create",
        argumentMode: {
            emptyHint: "Type a title for the new page…",
            getItems: (argQuery: string) => titledPageItems(argQuery),
            label: "title it",
            placeholder: "Title the new page…",
        },
    },
    {
        id: "actions:run-workflow",
        anonymous: false,
        icon: faPlay,
        keywords: "execute launch invoke start",
        subtitle: "Pick one of your workflows and open its run form",
        title: "Run workflow",
        argumentMode: {
            getItems: (argQuery: string) => myWorkflowItems(argQuery, ARGUMENT_LIMIT),
            // there is nothing to run without picking a workflow first
            immediate: true,
            label: "pick a workflow",
            placeholder: "Search my workflows…",
        },
    },
    {
        id: "actions:galaxy-ai",
        anonymous: false,
        configGate: (ctx) => Boolean(ctx.config.llm_api_configured),
        icon: faMagic,
        keywords: "chat assistant llm question help",
        subtitle: "Ask the Galaxy assistant about tools, workflows or errors",
        title: "Ask GalaxyAI",
        handler: (ctx: PaletteContext) => ctx.startNewChat?.(true),
        argumentMode: {
            emptyHint: "Type a question to start a new chat…",
            getItems: (argQuery: string) => galaxyAiItems(argQuery),
            label: "ask a question",
            placeholder: "Ask GalaxyAI…",
        },
    },
];

function actionItems(ctx: PaletteContext): PaletteItem[] {
    return ACTIONS.filter((action) => (action.anonymous || !ctx.isAnonymous) && (action.configGate?.(ctx) ?? true)).map(
        ({ anonymous: _anonymous, configGate: _configGate, ...item }) => item,
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
