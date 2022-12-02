<script setup>
import { ref, reactive, unref, watchEffect } from "vue";
import MonacoEditor from "monaco-editor-vue";

import { useElementBounding } from "@vueuse/core";

const editorContainer = ref(null);
const editorRef = ref(null);
const position = reactive(useElementBounding(editorContainer));

const props = defineProps({
    steps: {
        type: Object,
        required: true,
    },
});

const emit = defineEmits(["new-steps"]);

const code = ref(null);

watchEffect(() => {
    const cleanSteps = {};
    Object.entries(props.steps).forEach(([stepId, step]) => {
        const cleanStep = { ...step };
        delete cleanStep.config_form;
        delete cleanStep.tooltip;
        cleanSteps[stepId] = cleanStep;
    });
    code.value = JSON.stringify(cleanSteps, null, 2);
    unref(editorRef)?.editor;
    // const range = {startLineNumber: 140, endLineNumber: 150, startColumn: 1, endColumn: 1000}
    // editor?.revealRangeInCenter(range);
    // editor?.deltaDecorations([],
    //     [
    //         {
    //             options: {
    //                 inlineClassName: "myInlineDecoration",
    //             },
    //             range,
    //         }
    //     ]
    // )
});

const emitSteps = (val) => {
    // TODO: interferes with store
    // emit("new-steps", JSON.parse(val));
};
</script>
<template>
    <div ref="editorContainer">
        <MonacoEditor
            ref="editorRef"
            v-model="code"
            class="editor"
            language="js"
            :options="{ automaticLayout: true, fixedOverflowWidgets: true }"
            :width="position.width + 'px'"
            height="50vh"
            @change="emitSteps" />
    </div>
</template>
<style>
.myInlineDecoration {
    background: lightgreen;
}
</style>
