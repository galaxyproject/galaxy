<template>
    <div ref="editor" class="w-100" />
</template>

<script setup>
import ace from "ace-builds";
import { onMounted, ref, watch } from "vue";

const props = defineProps({
    theme: {
        type: String,
        default: "github_light_default",
    },
    mode: {
        type: String,
        default: "json",
    },
    value: {
        type: String,
        required: true,
    },
});

const emit = defineEmits(["update"]);

const editor = ref(null);

let aceEditor = null;

async function buildEditor() {
    const modePath = `ace/mode/${props.mode}`;
    const themePath = `ace/theme/${props.theme}`;
    const modeUrl = await import(`ace-builds/src-noconflict/mode-${props.mode}?url`);
    const themeUrl = await import(`ace-builds/src-noconflict/theme-${props.theme}?url`);
    ace.config.setModuleUrl(modePath, modeUrl);
    ace.config.setModuleUrl(themePath, themeUrl);
    aceEditor = ace.edit(editor.value, {
        highlightActiveLine: false,
        highlightGutterLine: false,
        maxLines: 30,
        minLines: 1,
        mode: modePath,
        showPrintMargin: false,
        theme: themePath,
        useWorker: false,
        value: props.value,
        wrap: true,
    });

    aceEditor.on("focus", () => {
        aceEditor.setOption("highlightActiveLine", true);
        aceEditor.setOption("highlightGutterLine", true);
        editor.value.classList.add("cell-code-focus");
    });

    aceEditor.on("blur", () => {
        aceEditor.setOption("highlightActiveLine", false);
        aceEditor.setOption("highlightGutterLine", false);
        editor.value.classList.remove("cell-code-focus");
    });

    aceEditor.on("change", () => {
        const newValue = aceEditor.getValue();
        emit("update", newValue);
    });
}

onMounted(() => {
    buildEditor();
});

watch(
    () => props.value,
    (newValue) => {
        if (aceEditor && newValue !== aceEditor.getValue()) {
            aceEditor.setValue(newValue, -1);
        }
    }
);
</script>

<style lang="scss">
@import "theme/blue.scss";
.cell-code-focus {
    background-color: $gray-100;
}
</style>
