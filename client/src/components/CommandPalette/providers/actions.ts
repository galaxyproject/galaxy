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

import { createPage } from "@/api/pages";
import { Toast } from "@/composables/toast";
import { useChatStore } from "@/stores/chatStore";
import { useHistoryStore } from "@/stores/historyStore";
import { usePageStore } from "@/stores/pageStore";
import { errorMessageAsString } from "@/utils/simple-error";
import { slugify } from "@/utils/slug";

import type { CommandPaletteProvider, PaletteContext, PaletteItem } from "../types";
import { type Gated, rankPaletteItems, visibleFor } from "../utilities";
import { myWorkflowItems } from "./workflows";

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
    try {
        await useHistoryStore().createNewHistory(name);
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

/** The backend rejects a slug that the user already has with this message */
function isSlugConflict(error: unknown): boolean {
    return /must be unique/i.test(String(errorMessageAsString(error, "")));
}

async function createTitledPage(title: string, ctx: PaletteContext) {
    // a title made of punctuation alone would leave no slug to send
    const slug = slugify(title, "page");
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
        // the `r:` scope renders from the store and stops asking the backend once
        // it holds every page, so the new one has to be seeded or it stays hidden
        usePageStore().savePages("my", [page], true);
        ctx.navigate?.(`/pages/editor?id=${page.id}`);
    } catch (error) {
        Toast.error(errorMessageAsString(error), "Failed to create report");
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
            title: `Create report titled '${title}'`,
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

const ACTIONS: Gated<PaletteItem>[] = [
    {
        anonymous: true,
        item: {
            id: "actions:upload",
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
    },
    {
        anonymous: false,
        item: {
            id: "actions:new-history",
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
    },
    {
        anonymous: false,
        item: {
            id: "actions:create-workflow",
            icon: faSitemap,
            keywords: "editor build new",
            subtitle: "Create a new workflow in the editor",
            title: "Create workflow",
            to: "/workflows/create",
        },
    },
    {
        anonymous: false,
        item: {
            id: "actions:import-workflow",
            icon: faFileImport,
            keywords: "upload trs url file",
            subtitle: "Import a workflow from file, URL or TRS",
            title: "Import workflow",
            to: "/workflows/import",
        },
    },
    {
        anonymous: false,
        item: {
            id: "actions:create-page",
            icon: faFileAlt,
            keywords: "markdown document report page notebook new",
            subtitle: "Create a new report and open the editor",
            title: "Create new report",
            to: "/pages/create",
            argumentMode: {
                emptyHint: "Type a title for the new report…",
                getItems: (argQuery: string) => titledPageItems(argQuery),
                label: "title it",
                placeholder: "Title the new report…",
            },
        },
    },
    {
        anonymous: false,
        item: {
            id: "actions:run-workflow",
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
    },
    {
        anonymous: false,
        configGate: (ctx) => Boolean(ctx.config.llm_api_configured),
        item: {
            id: "actions:galaxy-ai",
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
    },
];

export const actionsProvider: CommandPaletteProvider = {
    id: "actions",
    title: "Actions",
    emptyQueryItems(ctx: PaletteContext) {
        return visibleFor(ACTIONS, ctx);
    },
    search(query: string, ctx: PaletteContext) {
        return rankPaletteItems(visibleFor(ACTIONS, ctx), query);
    },
};
