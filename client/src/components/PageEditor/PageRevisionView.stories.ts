import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { expect, fn } from "storybook/test";
import { h, ref, watch } from "vue";

import { FAKE_PAGE_REVISION, PAGE_CURRENT_CONTENT, PAGE_PREVIOUS_CONTENT } from "./testData";

import PageRevisionView from "./PageRevisionView.vue";

type ViewMode = InstanceType<typeof PageRevisionView>["$props"]["viewMode"];

const meta = {
    title: "PageEditor/PageRevisionView",
    component: PageRevisionView,
    decorators: [withCurrentUser()],
    args: {
        revision: FAKE_PAGE_REVISION,
        currentContent: PAGE_CURRENT_CONTENT,
        previousContent: PAGE_PREVIOUS_CONTENT,
        isNewestRevision: false,
        isOldestRevision: false,
        viewMode: "preview",
        isReverting: false,
        onBack: fn(),
        onRestore: fn(),
    },
    render: (args) => ({
        setup() {
            const viewMode = ref<ViewMode>(args.viewMode);
            watch(
                () => args.viewMode,
                (mode) => {
                    viewMode.value = mode;
                },
            );
            return () =>
                h(PageRevisionView, {
                    ...args,
                    viewMode: viewMode.value,
                    "onUpdate:viewMode": (mode: ViewMode) => {
                        viewMode.value = mode;
                    },
                });
        },
    }),
} satisfies Meta<typeof PageRevisionView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Preview: Story = {};
export const ComparedWithCurrent: Story = { args: { viewMode: "changes_current" } };
export const ComparedWithPrevious: Story = { args: { viewMode: "changes_previous" } };
export const MatchesCurrent: Story = {
    play: async ({ canvas, step }) => {
        await step("Explain that this revision matches the current content", async () => {
            await expect(canvas.getByText("No changes — this revision matches the current content.")).toBeVisible();
            await expect(canvas.queryByText(/^\+\d+$/)).not.toBeInTheDocument();
            await expect(canvas.queryByText(/^-\d+$/)).not.toBeInTheDocument();
        });
    },
    args: { viewMode: "changes_current", currentContent: FAKE_PAGE_REVISION.content ?? "" },
};
export const MatchesPrevious: Story = {
    play: async ({ canvas, step }) => {
        await step("Explain that this revision matches its predecessor", async () => {
            await expect(canvas.getByText("No changes — this revision matches the previous revision.")).toBeVisible();
            await expect(canvas.queryByText(/^\+\d+$/)).not.toBeInTheDocument();
            await expect(canvas.queryByText(/^-\d+$/)).not.toBeInTheDocument();
        });
    },
    args: { viewMode: "changes_previous", previousContent: FAKE_PAGE_REVISION.content },
};
export const NewestRevision: Story = {
    args: { isNewestRevision: true, currentContent: FAKE_PAGE_REVISION.content ?? "" },
};
export const OldestRevision: Story = { args: { isOldestRevision: true, previousContent: null } };
export const RestoringRevision: Story = { args: { isReverting: true } };

export const ComparesCurrentAndReturnsToPreview: Story = {
    play: async ({ canvas, userEvent, step }) => {
        await step("Read the selected revision's preview", async () => {
            await expect(await canvas.findByRole("heading", { name: "Analysis report" })).toBeVisible();
            await expect(canvas.getByText(/Reads processed: 12000/)).toBeVisible();
            await expect(canvas.getByRole("button", { name: "Preview" })).toBeVisible();
        });
        await step("Compare this revision with the current page", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Compare to Current" }));
            await expect(canvas.getByRole("button", { name: "Compare to Current" })).toBeVisible();
            await expect(canvas.getByText("+3")).toBeVisible();
            await expect(canvas.getByText("-2")).toBeVisible();
            await expect(canvas.getByText("lines")).toBeVisible();
            for (const line of [
                "- Reads processed: 12000",
                "- Reference build: hg19",
                "+ Reads processed: 16000",
                "+ Reference build: hg38",
                "+ Aligner: Bowtie2",
            ]) {
                await expect(canvas.getByText(line, { exact: true })).toBeVisible();
            }
            await expect(canvas.queryByRole("heading", { name: "Analysis report" })).not.toBeInTheDocument();
        });
        await step("Return to the revision's rendered preview", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Preview" }));
            await expect(await canvas.findByRole("heading", { name: "Analysis report" })).toBeVisible();
            await expect(canvas.getByText(/Reads processed: 12000/)).toBeVisible();
            await expect(canvas.queryByText("+ Reads processed: 16000", { exact: true })).not.toBeInTheDocument();
            await expect(canvas.getByRole("button", { name: "Preview" })).toBeVisible();
        });
    },
};

export const ComparesPreviousAndReturnsToPreview: Story = {
    play: async ({ canvas, userEvent, step }) => {
        await step("Read the selected revision's preview", async () => {
            await expect(await canvas.findByRole("heading", { name: "Analysis report" })).toBeVisible();
            await expect(canvas.getByText(/Reads processed: 12000/)).toBeVisible();
            await expect(canvas.getByRole("button", { name: "Preview" })).toBeVisible();
        });
        await step("Compare this revision with its predecessor", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Compare to Previous" }));
            await expect(canvas.getByRole("button", { name: "Compare to Previous" })).toBeVisible();
            await expect(canvas.getByText("+2")).toBeVisible();
            await expect(canvas.getByText("-1")).toBeVisible();
            await expect(canvas.getByText("lines")).toBeVisible();
            for (const line of ["- Reads processed: 8000", "+ Reads processed: 12000", "+ Reference build: hg19"]) {
                await expect(canvas.getByText(line, { exact: true })).toBeVisible();
            }
            await expect(canvas.queryByRole("heading", { name: "Analysis report" })).not.toBeInTheDocument();
        });
        await step("Return to the revision's rendered preview", async () => {
            await userEvent.click(canvas.getByRole("button", { name: "Preview" }));
            await expect(await canvas.findByRole("heading", { name: "Analysis report" })).toBeVisible();
            await expect(canvas.getByText(/Reads processed: 12000/)).toBeVisible();
            await expect(canvas.queryByText("- Reads processed: 8000", { exact: true })).not.toBeInTheDocument();
            await expect(canvas.getByRole("button", { name: "Preview" })).toBeVisible();
        });
    },
};
