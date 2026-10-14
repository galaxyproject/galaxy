import loader from "@monaco-editor/loader";
import type { Decorator, Meta, StoryObj } from "@storybook/vue3-vite";
import { h, onMounted, onUnmounted, ref } from "vue";

import { NEW_TOOL_YAML } from "./customToolEditorDefaults";

import ToolSourceDisplay from "./ToolSourceDisplay.vue";

/** As CustomToolEditor does, use the installed Monaco engine and a local Vite worker instead of its CDN loader. */
const withLocalMonaco: Decorator = (story) => ({
    setup() {
        const ready = ref(false);
        const previousEnvironment = self.MonacoEnvironment;
        let active = true;
        onUnmounted(() => {
            active = false;
            if (ready.value) {
                self.MonacoEnvironment = previousEnvironment;
            }
        });
        onMounted(async () => {
            const [monaco, { default: EditorWorker }] = await Promise.all([
                import("monaco-editor/esm/vs/editor/editor.main.js"),
                import("monaco-editor/esm/vs/editor/editor.worker?worker"),
            ]);
            if (!active) {
                return;
            }
            self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
            loader.config({ monaco });
            ready.value = true;
        });
        return () => (ready.value ? h("div", { style: { display: "flex", height: "360px" } }, [h(story())]) : null);
    },
});

const meta = {
    title: "Tool/ToolSourceDisplay",
    component: ToolSourceDisplay,
    decorators: [withLocalMonaco],
    args: {
        language: "xml",
        code: `<tool id="cat1" name="Concatenate datasets" version="1.0.0">
    <command>cat '$input1' > '$out_file1'</command>
    <inputs>
        <param name="input1" type="data" label="Input dataset" />
    </inputs>
    <outputs>
        <data name="out_file1" format_source="input1" />
    </outputs>
</tool>`,
    },
} satisfies Meta<typeof ToolSourceDisplay>;

export default meta;
type Story = StoryObj<typeof meta>;

/** A traditional XML wrapper, shown read-only from the tool information dialog. */
export const XmlToolSource: Story = {};

/** A user-defined tool's YAML definition, shown with YAML syntax highlighting. */
export const YamlToolSource: Story = {
    args: { code: NEW_TOOL_YAML, language: "yaml" },
};
