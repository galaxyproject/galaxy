<script setup lang="ts">
import { BButton } from "bootstrap-vue";

import { FormEntry } from "./formUtil";

import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    title: string;
    inputs: Array<FormEntry> | null; // not fully reactive so make sure to not mutate this array
    submitTitle: string;
    loadingMessage: string;
}

defineProps<Props>();
const emit = defineEmits<{
    (e: "onSubmit", formData: any): void;
}>();

let formData: any;

function onChange(incoming: any) {
    formData = incoming;
}

async function handleSubmit() {
    emit("onSubmit", formData);
}
</script>
<template>
    <div>
        <LoadingSpan v-if="inputs == null" :message="loadingMessage" />
        <div v-else>
            <FormCard :title="title">
                <template v-slot:body>
                    <FormDisplay :inputs="inputs" @onChange="onChange" />
                </template>
            </FormCard>
            <div class="mt-3">
                <BButton id="submit" variant="primary" class="mr-1" @click="handleSubmit">
                    {{ submitTitle }}
                </BButton>
            </div>
        </div>
    </div>
</template>
