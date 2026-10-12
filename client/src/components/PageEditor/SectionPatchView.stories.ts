import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { fn } from "storybook/test";

import { PAGE_ORIGINAL_SECTIONS, PAGE_PROPOSED_SECTIONS } from "./testData";

import SectionPatchView from "./SectionPatchView.vue";

const meta = {
    title: "PageEditor/SectionPatchView",
    component: SectionPatchView,
    decorators: [withCurrentUser()],
    args: {
        original: PAGE_ORIGINAL_SECTIONS,
        proposed: PAGE_PROPOSED_SECTIONS,
        onAccept: fn(),
        onReject: fn(),
    },
} satisfies Meta<typeof SectionPatchView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const TwoSectionProposal: Story = {};

export const SingleSectionProposal: Story = {
    args: { original: "# Results\nExpression counts pending.", proposed: "# Results\nExpression counts ready." },
};

export const UnchangedProposal: Story = {
    args: { original: "# Methods\nReads aligned with STAR.", proposed: "# Methods\nReads aligned with STAR." },
};

export const StaleProposal: Story = { args: { stale: true } };
