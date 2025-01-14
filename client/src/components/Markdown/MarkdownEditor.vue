<template>
    <div id="columns" class="d-flex">
        <TextEditor :title="title" :markdown-text="markdownText" :steps="steps" :mode="mode" />
    </div>
</template>

<script>
import TextEditor from "./Editor/TextEditor.vue";

export default {
    components: {
        TextEditor,
    },
    props: {
        markdownText: {
            type: String,
            default: null,
        },
        steps: {
            type: Object,
            default: null,
        },
        title: {
            type: String,
            default: null,
        },
        mode: {
            type: String,
            default: "report",
        },
    },
};
</script>
