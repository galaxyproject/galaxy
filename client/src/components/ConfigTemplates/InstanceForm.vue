<script setup lang="ts">
import { BButton } from "bootstrap-vue";

import { type FormEntry } from "./formUtil";

import ForceActionButton from "./ForceActionButton.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    title: string;
    inputs?: Array<FormEntry>; // not fully reactive so make sure to not mutate this array
    submitTitle: string;
    loadingMessage: string;
    busy: boolean;
    showForceActionButton?: boolean;
}

withDefaults(defineProps<Props>(), {
    inputs: undefined,
    showForceActionButton: false,
});

const emit = defineEmits<{
    (e: "onSubmit", formData: any): void;
    (e: "onForceSubmit", formData: any): void;
}>();

let formData: any;

function onChange(incoming: any) {
    formData = incoming;
}

async function handleSubmit() {
    emit("onSubmit", formData);
}

async function handleForceSubmit() {
    emit("onForceSubmit", formData);
}
</script>
<template>
    <div>
        <LoadingSpan v-if="inputs == undefined" :message="loadingMessage" />
        <div v-else>
            <FormCard :title="title">
                <template v-slot:body>
                    <FormDisplay :inputs="inputs" @onChange="onChange" />
                </template>
            </FormCard>
            <div class="mt-3">
                <BButton id="submit" variant="primary" class="mr-1" :disabled="busy" @click="handleSubmit">
                    {{ submitTitle }}
                </BButton>
                <ForceActionButton v-show="showForceActionButton" :action="submitTitle" @click="handleForceSubmit">
                </ForceActionButton>
            </div>
        </div>
    </div>
</template>
