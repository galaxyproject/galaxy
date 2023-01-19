<script setup>
const props = defineProps({
    value: {
        type: Object,
    },
    target: {
        type: Object,
        default: null,
    },
});

function readFile() {
    this.console.log("uploaded file!");
}
</script>

<template>
    <div>
        <input type="file" @change="readFile" ref="file" />
    </div>
</template>
