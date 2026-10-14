import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { getActivePinia } from "pinia";
import { expect } from "storybook/test";
import { h, nextTick, onBeforeUnmount, onUnmounted, ref, watch } from "vue";

import { http } from "@/api/client/__mocks__/http";
import { activitySettingsHandlers } from "@/components/ActivityBar/test_fixtures";
import { toolPanelHandlers } from "@/components/Panels/test_fixtures";
import { useHashedUserId } from "@/composables/hashedUserId";
import { useToolStore } from "@/stores/toolStore";
import { ensureDefined } from "@/utils/assertions";

import { pageHandler, PUBLISHED_PAGE } from "./test_fixtures";

import PageView from "./PageView.vue";

const VIEWER = getFakeRegisteredUser();
const AUTHOR = getFakeRegisteredUser({ id: "a7c1f3b29e4d6058", username: PUBLISHED_PAGE.username });

// Restoring a reused store flushes its watcher before the next mount can seed the same preference.
const pendingPanelCleanup = new Map<string, Promise<void>>();

/** The published scene starts in Full Tool Panel without replacing its real catalog requests. */
const withFullToolPanel: Decorator = (story) => ({
    setup() {
        const pinia = ensureDefined(getActivePinia());
        const { hashedUserId } = useHashedUserId(ref(VIEWER));
        const ready = ref(false);
        let mounted = true;
        let starting = false;
        let release: (() => void) | undefined;
        let restoreAfterUnmount: (() => void) | undefined;
        onUnmounted(() => restoreAfterUnmount?.());
        onBeforeUnmount(() => {
            mounted = false;
            release?.();
        });
        watch(
            hashedUserId,
            async (hash) => {
                if (!hash || starting || !mounted) {
                    return;
                }
                starting = true;
                const key = `tool-store-view-${hash}`;
                await pendingPanelCleanup.get(key);
                if (!mounted) {
                    return;
                }
                const previousRaw = localStorage.getItem(key);
                const previousStore = pinia._s.get("toolStore");
                const previousState = pinia.state.value.toolStore;
                const previousValues = { ...previousState };
                const previousView = previousStore?.currentPanelView;
                localStorage.setItem(key, "default");
                const store = useToolStore(pinia);
                store.currentPanelView = "default";
                const restoreStorage = () => {
                    if (previousRaw === null) {
                        localStorage.removeItem(key);
                    } else {
                        localStorage.setItem(key, previousRaw);
                    }
                };
                release = () => {
                    if (previousStore) {
                        store.currentPanelView = previousView;
                        const cleanup = nextTick().then(restoreStorage);
                        pendingPanelCleanup.set(key, cleanup);
                        void cleanup.then(() => {
                            if (pendingPanelCleanup.get(key) === cleanup) {
                                pendingPanelCleanup.delete(key);
                            }
                        });
                    } else {
                        store.$dispose();
                        if (previousState === undefined) {
                            delete pinia.state.value.toolStore;
                        } else {
                            Object.assign(previousState, previousValues);
                            pinia.state.value.toolStore = previousState;
                        }
                        restoreAfterUnmount = restoreStorage;
                    }
                };
                ready.value = true;
            },
            { immediate: true },
        );
        return () => (ready.value ? h(story()) : null);
    },
});

/**
 * A notebook at `/published/page`, viewed by a signed-in user who isn't its author. The published
 * view's activity bar opens the tool panel, which reloads that user, their unprivileged tools and the toolbox.
 */
const meta = {
    title: "Page/PageView",
    component: PageView,
    decorators: [withCurrentUser(() => VIEWER)],
    args: { pageId: PUBLISHED_PAGE.id },
    parameters: {
        msw: {
            handlers: {
                page: pageHandler(),
                currentUser: http.get("/api/users/{user_id}", ({ response }) => response(200).json(VIEWER)),
                unprivilegedTools: activitySettingsHandlers.permittedTools,
                ...toolPanelHandlers,
            },
        },
    },
} satisfies Meta<typeof PageView>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** Waits for the notebook's Markdown, which shows the page has loaded. */
async function seeNotebookContent({ canvas, step }: PlayContext) {
    await step("See the notebook's content", async () => {
        await expect(await canvas.findByRole("heading", { name: "Methods" }, { timeout: 5000 })).toBeVisible();
        await expect(canvas.getByText("Reads were trimmed with Cutadapt and aligned with HISAT2.")).toBeVisible();
    });
}

/** Neither the chrome's links (activity bar, About panel) nor the "About this Notebook" heading shows. */
async function seeNoChrome({ canvas, step }: PlayContext) {
    await step("See no Galaxy chrome: no links and no About panel", async () => {
        await expect(canvas.queryAllByRole("link")).toHaveLength(0);
        await expect(canvas.queryByRole("heading", { name: "About this Notebook" })).toBeNull();
    });
}

/** The published notebook in Galaxy's chrome, with its "About this Notebook" panel. */
export const Published: Story = {
    decorators: [withFullToolPanel],
    play: async (context) => {
        const { canvas, step } = context;
        await seeNotebookContent(context);
        await step("See the activity bar's tool panel load", async () => {
            await expect(
                await canvas.findByRole("button", { name: "Collection Operations" }, { timeout: 5000 }),
            ).toBeVisible();
        });
        await step("See the About panel name the notebook and its author", async () => {
            await expect(canvas.getByRole("heading", { level: 1, name: "About this Notebook" })).toBeVisible();
            await expect(canvas.getByRole("heading", { level: 2, name: "Yeast heat-shock RNA-seq" })).toBeVisible();
            const author = canvas.getByRole("heading", { level: 2, name: "Author" });
            await expect(author.nextElementSibling).toHaveTextContent(/^jdoe$/);
            await expect(canvas.getByRole("link", { name: "Published Notebooks by jdoe" })).toBeVisible();
        });
    },
};

/** Without chrome, as the sharing page's embed code and the notebook list's "View in Window" open it. */
export const Embedded: Story = {
    args: { embed: true },
    play: async (context) => {
        await seeNotebookContent(context);
        await seeNoChrome(context);
        await context.step("See no toolbar back to the editor", async () => {
            await expect(context.canvas.queryAllByRole("button")).toHaveLength(0);
        });
    },
};

/** `/published/page?displayOnly=true`, opened by its author: no chrome, and a toolbar back to the editor. */
export const DisplayOnly: Story = {
    args: { displayOnly: true },
    parameters: viewedBy(AUTHOR),
    play: async (context) => {
        const { canvas, step } = context;
        await seeNotebookContent(context);
        await seeNoChrome(context);
        await step("See a toolbar with Edit Notebook, then the notebook's title", async () => {
            const editButton = canvas.getByRole("button", { name: "Edit Notebook" });
            await expect(editButton).toBeVisible();
            await expect(canvas.getAllByRole("button")).toEqual([editButton]);
            await expect(editButton.parentElement).toHaveTextContent(
                /^\s*Edit Notebook\s*Yeast heat-shock RNA-seq\s*$/,
            );
        });
    },
};
