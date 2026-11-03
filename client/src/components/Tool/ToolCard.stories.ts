import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { withLoadedConfig } from "@tests/test-data/config";
import { viewedBy, withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";
import { expect, screen, within } from "storybook/test";
import { type Component, defineComponent, h, ref } from "vue";

import { configurationHandler, http } from "@/api/client/__mocks__/http";

import ToolCard from "./ToolCard.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

const FASTQC_VERSIONS = ["0.73+galaxy0", "0.74+galaxy1"];

/** The tool form's options for FastQC at `version`, as the tool's build request answers them. */
function fastqcAt(version: string, versions = FASTQC_VERSIONS) {
    return {
        id: `toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/${version}`,
        name: "FastQC",
        description: "Read Quality reports",
        version,
        versions,
        sharable_url: "https://toolshed.g2.bx.psu.edu/view/devteam/fastqc/5ec4f1a9e7c3",
        help: "<p><strong>What it does</strong></p><p>FastQC runs quality control checks on raw sequence data.</p>",
        help_format: "restructuredtext",
        citations: false,
        tool_shed_repository: { name: "fastqc", owner: "devteam", tool_shed: "toolshed.g2.bx.psu.edu" },
    };
}

/** The card's props for FastQC at `version`, as the tool form passes them on load. */
function fastqcCard(version: string, versions = FASTQC_VERSIONS) {
    const options = fastqcAt(version, versions);
    return { id: options.id, version, title: options.name, description: options.description, options };
}

/** As on the tool form: "Run Tool" covers the parameters with a backdrop while the job is submitted. */
export const ToolCardWithRunButton = defineComponent({
    name: "ToolCardWithRunButton",
    inheritAttrs: false,
    setup(_, { attrs }) {
        const running = ref(false);
        return () =>
            h(
                ToolCard as Component,
                { ...attrs, disabled: running.value },
                {
                    buttons: () =>
                        h(
                            GButton,
                            {
                                size: "small",
                                "data-description": "run tool button",
                                onClick: () => (running.value = true),
                            },
                            () => "Run Tool",
                        ),
                },
            );
    },
});

const meta = {
    title: "Tool/ToolCard",
    component: ToolCard,
    excludeStories: ["ToolCardWithRunButton"],
    decorators: [withLoadedConfig, withCurrentUser(() => getFakeRegisteredUser({ is_admin: true }))],
    args: { ...fastqcCard("0.74+galaxy1"), messageText: "" },
    parameters: {
        msw: {
            handlers: {
                configuration: configurationHandler({ enable_tool_source_display: false }),
                webhooks: http.untyped.get("/api/webhooks", () => HttpResponse.json([])),
            },
        },
    },
} satisfies Meta<typeof ToolCard>;

export default meta;
type Story = StoryObj<typeof meta>;
type PlayContext = Parameters<NonNullable<Story["play"]>>[0];

/** The card waits on the configuration, so the first wait gets longer than the 1s default. */
const CONFIG_LOAD = { timeout: 5000 };

/** Waits for the card's heading, "FastQC", before anything else is read. */
async function seeToolHeading({ canvas, step }: PlayContext) {
    await step("See the tool's name as the page heading", async () => {
        await expect(await canvas.findByRole("heading", { level: 1, name: "FastQC" }, CONFIG_LOAD)).toBeVisible();
    });
}

/**
 * The accessible name of the "Newer version available" badge.
 *
 * Pre-existing bug, tolerated here: `v-g-tooltip` names the badge with its tooltip, so its
 * visible text is left out of its name.
 */
const NEWER_VERSION_BADGE = /^(Newer version available|Switch to the latest available tool version)$/;

/** Checks the "Newer version available" badge is absent; call after `seeToolHeading`. */
async function seeNoNewerVersionBadge({ canvas, step }: PlayContext) {
    await step("See no badge offering a newer version", async () => {
        await expect(canvas.queryByRole("button", { name: NEWER_VERSION_BADGE })).not.toBeInTheDocument();
        await expect(canvas.queryByText("Newer version available")).not.toBeInTheDocument();
    });
}

/** Opens the tool's options menu and reads its items, in order. */
function offersToolOptions(items: string[]) {
    return async (context: PlayContext) => {
        const { canvas, step, userEvent } = context;
        await seeToolHeading(context);
        await step("See the options menu closed", async () => {
            await expect(canvas.queryByRole("menu")).not.toBeInTheDocument();
        });
        await step(`Open the tool's options: ${items.join(", ")}`, async () => {
            await userEvent.click(canvas.getByRole("button", { name: "View all Options" }));
            const menu = await canvas.findByRole("menu", { name: "View all Options" });
            const names = within(menu)
                .getAllByRole("menuitem")
                .map((item) => item.textContent?.trim());
            await expect(menu).toBeVisible();
            await expect(names).toEqual(items);
        });
    };
}

/** An admin opens the latest of FastQC's versions: the versions menu, and the admin's tool options. */
export const LatestVersion: Story = {
    play: async (context) => {
        const { canvas, step } = context;
        await seeToolHeading(context);
        await step("Read the tool's description and version", async () => {
            await expect(canvas.getByText("Read Quality reports")).toBeVisible();
            await expect(canvas.getByText("(Galaxy Version 0.74+galaxy1)")).toBeVisible();
        });
        await step("See a menu of the tool's versions", async () => {
            await expect(canvas.getByRole("button", { name: "Select Versions" })).toBeVisible();
        });
        await seeNoNewerVersionBadge(context);
    },

    // TODO a11y: nested-interactive (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** An admin opens the options menu: copy, download, view source and the Tool Shed page. */
export const OffersAdminToolOptions: Story = {
    play: offersToolOptions(["Copy Link", "Copy Tool ID", "Download", "View Tool source", "See in Tool Shed"]),

    // TODO a11y: nested-interactive (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A user who isn't an admin can't download the tool or view its source. */
export const OffersUserToolOptions: Story = {
    parameters: {
        ...viewedBy(getFakeRegisteredUser()),
        // TODO a11y: nested-interactive (2026-10-10 audit).
        a11y: { test: "todo" },
    },
    play: offersToolOptions(["Copy Link", "Copy Tool ID", "See in Tool Shed"]),
};

/** An older FastQC version: a badge offers the newest one. */
export const NewerVersionAvailable: Story = {
    args: fastqcCard("0.73+galaxy0"),
    play: async (context) => {
        const { canvas, step, userEvent } = context;
        await seeToolHeading(context);
        await step("Hover the badge offering the newest version to read what it does", async () => {
            const badge = canvas.getByRole("button", { name: NEWER_VERSION_BADGE });
            await expect(badge).toHaveTextContent(/^Newer version available$/);
            await expect(badge).toBeVisible();
            // The card's icon buttons keep their own tooltips in the DOM, so this one is found by its name.
            const tooltip = { name: "Switch to the latest available tool version" };
            await expect(screen.queryByRole("tooltip", tooltip)).not.toBeInTheDocument();
            await userEvent.hover(badge);
            await expect(await screen.findByRole("tooltip", tooltip)).toHaveTextContent(
                /^Switch to the latest available tool version$/,
            );
            await userEvent.unhover(badge);
            await expect(screen.queryByRole("tooltip", tooltip)).not.toBeInTheDocument();
        });
    },

    // TODO a11y: label-content-name-mismatch, nested-interactive (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** A tool with one version: no versions menu and no badge. */
export const SingleVersion: Story = {
    args: fastqcCard("0.74+galaxy1", ["0.74+galaxy1"]),
    play: async (context) => {
        const { canvas, step } = context;
        await seeToolHeading(context);
        await step("See no menu of versions", async () => {
            await expect(canvas.queryByRole("button", { name: "Select Versions" })).not.toBeInTheDocument();
        });
        await seeNoNewerVersionBadge(context);
    },

    // TODO a11y: nested-interactive (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};

/** With the tool form's Run Tool button, which covers the card while the job is submitted. */
export const WithRunButton: Story = {
    render: (args) => () => h(ToolCardWithRunButton, args),

    // TODO a11y: nested-interactive (2026-10-10 audit).
    parameters: { a11y: { test: "todo" } },
};
