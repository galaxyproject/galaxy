import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { withLoadedConfig } from "@tests/test-data/config";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { HttpResponse } from "msw";
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

/** An admin opens the latest of FastQC's versions: the versions menu, and the admin's tool options. */
export const LatestVersion: Story = {};

/** An older FastQC version: a badge offers the newest one. */
export const NewerVersionAvailable: Story = { args: fastqcCard("0.73+galaxy0") };

/** A tool with one version: no versions menu and no badge. */
export const SingleVersion: Story = { args: fastqcCard("0.74+galaxy1", ["0.74+galaxy1"]) };

/** With the tool form's Run Tool button, which covers the card while the job is submitted. */
export const WithRunButton: Story = {
    render: (args) => () => h(ToolCardWithRunButton, args),
};
