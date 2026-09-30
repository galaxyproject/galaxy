<script setup>
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormFile } from "bootstrap-vue";
import { computed, ref } from "vue";

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
        <BFormFile v-model="file" class="mb-1" @input="readFile" />
        <div v-if="waiting">
            <FontAwesomeIcon :icon="faSpinner" spin />
            Uploading File...
        </div>
        <textarea v-show="currentValue" v-model="currentValue" class="ui-textarea" disabled />
    </div>
</template>
