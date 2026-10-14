import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";

import { http } from "@/api/client/__mocks__/http";
import { activitySettingsHandlers } from "@/components/ActivityBar/test_fixtures";
import { toolPanelHandlers } from "@/components/Panels/test_fixtures";

import { pageHandler, PUBLISHED_PAGE } from "./test_fixtures";

import PageView from "./PageView.vue";

const VIEWER = getFakeRegisteredUser();
const AUTHOR = getFakeRegisteredUser({ id: "a7c1f3b29e4d6058", username: PUBLISHED_PAGE.username });

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

/** The published notebook in Galaxy's chrome, with its "About this Notebook" panel. */
export const Published: Story = {};

/** Without chrome, as the sharing page's embed code and the notebook list's "View in Window" open it. */
export const Embedded: Story = { args: { embed: true } };

/** `/published/page?displayOnly=true`, opened by its author: no chrome, and a toolbar back to the editor. */
export const DisplayOnly: Story = {
    args: { displayOnly: true },
    parameters: viewedBy(AUTHOR),
};
