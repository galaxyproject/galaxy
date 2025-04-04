<template>
    <div ref="editor" class="w-100" />
</template>

<script setup>
import ace from "ace-builds";
import { debounce } from "lodash";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const DELAY = 300;

const props = defineProps({
    theme: {
        type: String,
        default: "github_light_default",
    },
    maxLines: {
        type: Number,
        default: 99999,
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

const emit = defineEmits(["change"]);

const editor = ref(null);

let aceEditor = null;

const emitChange = debounce((newValue) => {
    emit("change", newValue);
}, DELAY);

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
        maxLines: props.maxLines,
        minLines: 1,
        mode: modePath,
        showPrintMargin: false,
        theme: themePath,
        useWorker: false,
        value: props.value,
        wrap: true,
    });

    aceEditor.on("blur", () => {
        aceEditor.setOption("highlightActiveLine", false);
        aceEditor.setOption("highlightGutterLine", false);
        editor.value.classList.remove("cell-code-focus");
    });

    aceEditor.on("change", () => {
        const newValue = aceEditor.getValue();
        emitChange(newValue);
    });

    aceEditor.on("focus", () => {
        aceEditor.setOption("highlightActiveLine", true);
        aceEditor.setOption("highlightGutterLine", true);
        editor.value.classList.add("cell-code-focus");
    });
}

onBeforeUnmount(() => {
    emitChange.cancel();
});

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
