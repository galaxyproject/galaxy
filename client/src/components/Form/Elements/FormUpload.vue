<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormFile } from "bootstrap-vue";
import { computed, ref } from "vue";

library.add(faSpinner);

interface Props {
    value: string | ArrayBuffer | unknown;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input", value: string | ArrayBuffer | unknown): void;
}>();

const file = ref(null);
const waiting = ref(false);

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
            currentValue.value = reader.result ?? "";
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
