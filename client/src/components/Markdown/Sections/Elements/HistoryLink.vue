<template>
    <div>
        <b-link
            v-if="showLink"
            data-description="history import link"
            :data-history-id="args.history_id"
            @click="onClick">
            Click to Import History: {{ name }}.
        </b-link>
        <div v-if="imported" class="text-success">
            <FontAwesomeIcon icon="check" class="mr-1" />
            <span>Successfully Imported History: {{ name }}!</span>
        </div>
        <div v-if="!!error" class="text-danger">
            <FontAwesomeIcon icon="exclamation-triangle" class="mr-1" />
            <span>Failed to Import History: {{ name }}!</span>
            <span>{{ error }}</span>
        </div>
    </div>
</template>

<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
//@ts-ignore
import { withPrefix } from "utils/redirect";
//@ts-ignore
import { errorMessageAsString } from "utils/simple-error";
import { computed, ref } from "vue";

interface Props {
    args: {
        history_id: string;
    };
    histories: Record<string, { name: string }>;
}

const props = defineProps<Props>();

const imported = ref(false);
const error = ref<string | null>(null);

const name = computed(() => props.histories[props.args.history_id]?.name || "");
const showLink = computed(() => !imported.value && !error.value);

const onClick = async () => {
    try {
        await axios.post(withPrefix("/api/histories"), { history_id: props.args.history_id });
        imported.value = true;
    } catch (e) {
        error.value = errorMessageAsString(e);
    }
};
</script>
