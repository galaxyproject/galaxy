<script setup>
import { ref, defineEmits, reactive } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

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
const waiting = ref(false);

function readFile() {
    const fileContent = file.value && file.value.files[0];
    var reader = new FileReader();
    if (fileContent) {
        waiting.value = true;
        reader.onload = () => {
            const result = reader.result;
            emit("input", result);
            currentValue.value = result;
            waiting.value = false;
        };
        reader.readAsText(fileContent);
    }
}
</script>

<template>
    <div>
        <input ref="file" type="file" class="mb-1" @change="readFile" />
        <div v-if="waiting">
            <font-awesome-icon icon="spinner" spin />
            Uploading File ...
        </div>
        <textarea v-show="currentValue.value" v-model="currentValue.value" class="ui-textarea" disabled></textarea>
    </div>
</template>
