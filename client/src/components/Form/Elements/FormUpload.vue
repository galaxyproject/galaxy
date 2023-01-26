<script setup>
import { ref, defineEmits, computed } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
const props = defineProps({
    value: ""
});
const file = ref(null);
const emit = defineEmits(["input"]);
const currentValue = computed({
    get() {
        return props.value;
    },
    set(newValue) {
        emit("input", newValue);
    },
});
const waiting = ref(false);
function readFile() {
    const fileContent = file.value && file.value.files[0];
    var reader = new FileReader();
    if (fileContent) {
        waiting.value = true;
        reader.onload = () => {
            currentValue.value = reader.result;
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
            Uploading File...
        </div>
        <textarea v-show="currentValue" v-model="currentValue" class="ui-textarea" disabled></textarea>
    </div>
</template>