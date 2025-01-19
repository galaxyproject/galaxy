<template>
    <div ref="editor" class="w-100" />
</template>

<script setup>
import ace from "ace-builds";
import { onMounted, ref } from "vue";

// Props
const props = defineProps({
    modelValue: {
        type: String,
        required: true,
    },
    theme: {
        type: String,
        default: "github_light_default",
    },
    mode: {
        type: String,
        default: "javascript",
    },
});

// Emit for v-model
//const emit = defineEmits(['update:modelValue']);

const editor = ref(null); // Reference to the editor DOM element

async function buildEditor() {
    const modePath = `ace/mode/${props.mode}`;
    const themePath = `ace/theme/${props.theme}`;
    const modeUrl = await import(`ace-builds/src-noconflict/mode-${props.mode}?url`);
    const themeUrl = await import(`ace-builds/src-noconflict/theme-${props.theme}?url`);
    ace.config.setModuleUrl(modePath, modeUrl);
    ace.config.setModuleUrl(themePath, themeUrl);
    const aceEditor = ace.edit(editor.value, {
        highlightActiveLine: false,
        highlightGutterLine: false,
        maxLines: 30,
        minLines: 1,
        mode: modePath,
        showPrintMargin: false,
        theme: themePath,
        useWorker: false,
        value: props.modelValue,
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

    /*/ Update modelValue when editor content changes
    // Set the mode (language) if needed
    aceEditor.session.on('change', () => {
      const newValue = aceEditor.getValue();
      emit('update:modelValue', newValue);
    });*/
}

// Initialize the Ace editor
onMounted(() => {
    buildEditor();
});

/*/ Watch for external modelValue changes and update the editor
  watch(
    () => props.modelValue,
    (newValue) => {
      if (newValue !== aceEditor.getValue()) {
        aceEditor.setValue(newValue, -1); // -1 prevents cursor jump
      }
    }
  );*/
</script>

<style lang="scss">
@import "theme/blue.scss";
.cell-code-focus {
    background-color: $gray-100;
}
</style>
