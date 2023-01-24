<script setup>
import { ref, defineEmits, reactive } from "vue";

const props = defineProps({
    value: {
        type: String,
        default: "",
    },
});

const file = ref(null);
const emit = defineEmits(["input"]);
const currentValue = reactive({
    value: props.value,
});

function readFile() {
    const fileContent = file.value && file.value.files[0];
    var reader = new FileReader();
    if (fileContent) {
        reader.onload = () => {
            const result = reader.result;
            emit("input", result);
            currentValue.value = result;
        };
        reader.readAsText(fileContent);
    }
}
</script>

<template>
    <div>
        <input ref="file" type="file" class="mb-1" @change="readFile" />
        <textarea v-show="currentValue.value" v-model="currentValue.value" class="ui-textarea" disabled></textarea>
    </div>
</template>
