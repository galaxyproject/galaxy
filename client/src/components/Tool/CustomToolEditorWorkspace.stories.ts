import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { getFakeRegisteredUser } from "@tests/test-data";
import { withCurrentUser } from "@tests/test-data/currentUser";
import { withToasts } from "@tests/test-data/toasts";
import { defineComponent, h, ref, watch } from "vue";

import { NEW_TOOL_YAML } from "./customToolEditorDefaults";

import AuthoringHelpPanel from "./AuthoringHelpPanel.vue";
import CustomToolEditorWorkspace from "./CustomToolEditorWorkspace.vue";

/** The surrounding tool form supplies an editable YAML slot and its documentation toggle. */
export const WorkspaceWithSlots = defineComponent({
    name: "WorkspaceWithSlots",
    props: { documentationVisible: Boolean },
    setup(props) {
        const documentationVisible = ref(props.documentationVisible);
        const source = ref(NEW_TOOL_YAML);
        watch(
            () => props.documentationVisible,
            (visible) => {
                documentationVisible.value = visible;
            },
        );
        return () =>
            h("div", { style: { display: "flex", flexDirection: "column", height: "640px" } }, [
                h(
                    "button",
                    {
                        type: "button",
                        class: "mb-2 align-self-start",
                        onClick: () => {
                            documentationVisible.value = !documentationVisible.value;
                        },
                    },
                    documentationVisible.value ? "Hide documentation" : "Show documentation",
                ),
                h(
                    CustomToolEditorWorkspace,
                    { documentationVisible: documentationVisible.value },
                    {
                        editor: () =>
                            h("textarea", {
                                "aria-label": "Tool YAML source",
                                "data-description": "tool yaml editor",
                                style: { width: "100%", height: "100%", resize: "none" },
                                value: source.value,
                                onInput: (event: Event) => {
                                    source.value = (event.target as HTMLTextAreaElement).value;
                                },
                            }),
                        documentation: () =>
                            h("article", { "data-description": "tool documentation" }, [
                                h(AuthoringHelpPanel, { class: "p-3" }),
                            ]),
                    },
                ),
            ]);
    },
});

const meta = {
    title: "Tool/CustomToolEditorWorkspace",
    component: CustomToolEditorWorkspace,
    excludeStories: ["WorkspaceWithSlots"],
    render: (args) => () => h(WorkspaceWithSlots, args),
    decorators: [
        withToasts,
        withCurrentUser(() =>
            getFakeRegisteredUser({ id: "f2db41e1fa331b3e", email: "alice@example.org", username: "alice" }),
        ),
    ],
    args: { documentationVisible: false },
    // The harness owns the live toggle; this arg chooses the story's starting state.
    argTypes: { documentationVisible: { control: false } },
} satisfies Meta<typeof CustomToolEditorWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The workspace concentrates on YAML editing until its parent form opens documentation. */
export const EditorOnly: Story = {};

/** The actual authoring guide sits alongside the editable YAML slot; it can expand to fill the workspace. */
export const WithDocumentation: Story = {
    args: { documentationVisible: true },
};
