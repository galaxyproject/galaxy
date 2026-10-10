import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeAnonymousUser } from "@tests/test-data";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";
import { h, onMounted, onUnmounted, watch } from "vue";

import { http } from "@/api/client/__mocks__/http";
import toolsList from "@/components/ToolsView/testData/toolsList.json";
import { useCommandPalette } from "@/composables/useCommandPalette";

import CommandPalette from "./CommandPalette.vue";

/**
 * The palette lives closed in the app shell until ctrl/cmd+k opens it, which it only does once
 * the configuration has loaded. Open it then, once mounted so its dialog exists, and close it
 * again on unmount, since the open state is shared by the whole app.
 */
const withPaletteOpen: Decorator = (story) => ({
    setup() {
        const { closePalette, openPalette, paletteEnabled } = useCommandPalette();
        onMounted(() => {
            watch(paletteEnabled, (enabled) => enabled && openPalette(), { immediate: true });
        });
        onUnmounted(closePalette);
    },
    render: () => h(story()),
});

const meta = {
    title: "CommandPalette",
    component: CommandPalette,
    decorators: [withPaletteOpen, withCurrentUser()],
    parameters: {
        msw: {
            handlers: {
                // the first open loads every tool, so recent tools resolve to their names
                tools: http.untyped.get("/api/tools", () => HttpResponse.json(toolsList)),
                unprivilegedTools: http.get("/api/unprivileged_tools", ({ response }) => response(200).json([])),
            },
        },
    },
} satisfies Meta<typeof CommandPalette>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Opened by a signed-in user with nothing typed: the actions and pages they can jump to. */
export const Open: Story = {};

/**
 * Opened by a visitor without an account: fewer actions and pages, and a scope that needs an
 * account (`w:` for my workflows) offers a login instead.
 */
export const AnonymousVisitor: Story = { parameters: viewedBy(getFakeAnonymousUser()) };
