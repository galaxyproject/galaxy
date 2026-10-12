import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { fn } from "storybook/test";
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
    args: { viewMode: "changes_current", currentContent: FAKE_PAGE_REVISION.content ?? "" },
};
export const MatchesPrevious: Story = {
    args: { viewMode: "changes_previous", previousContent: FAKE_PAGE_REVISION.content },
};
export const NewestRevision: Story = {
    args: { isNewestRevision: true, currentContent: FAKE_PAGE_REVISION.content ?? "" },
};
export const OldestRevision: Story = { args: { isOldestRevision: true, previousContent: null } };
export const RestoringRevision: Story = { args: { isReverting: true } };
