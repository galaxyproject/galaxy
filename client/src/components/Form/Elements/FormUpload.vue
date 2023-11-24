<script setup>
import { ref, computed } from "vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
const props = defineProps({
    value: {
        required: true,
    },
});
const file = ref(null);
const waiting = ref(false);

const emit = defineEmits(["input"]);

const currentValue = computed({
    get() {
        return props.value;
    },
    set(newValue) {
        emit("input", newValue);
    },
});

function readFile() {
    var reader = new FileReader();
    if (file.value) {
        waiting.value = true;
        reader.onload = () => {
            currentValue.value = reader.result;
            waiting.value = false;
        };
        reader.readAsText(file.value);
    }
}
</script>

<template>
    <div>
        <b-form-file v-model="file" class="mb-1" @input="readFile" />
        <div v-if="waiting">
            <font-awesome-icon icon="spinner" spin />
            Uploading File...
        </div>
        <textarea v-show="currentValue" v-model="currentValue" class="ui-textarea" disabled />
    </div>
</template>
