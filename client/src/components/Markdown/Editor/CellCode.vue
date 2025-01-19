<template>
    <div ref="editor" class="editor" />
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
    ace.edit(editor.value, {
        value: props.modelValue,
        theme: themePath,
        mode: modePath,
        showPrintMargin: false,
        useWorker: false,
    });

    /*/ Update modelValue when editor content changes
    // Set the mode (language) if needed
    editor.session.setMode("ace/mode/javascript");
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

<style>
.editor {
    width: 100%;
    height: 300px;
    border: 1px solid #ddd;
}
</style>
