<script setup lang="ts">
import FormCard from "@/components/Form/FormCard.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    title: string;
    inputs: any | null; // not fully reactive so make sure these are ready to go when loading is false
    submitTitle: string;
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
        <LoadingSpan v-if="inputs == null" message="Loading object store template and instance information" />
        <div v-else>
            <FormCard :title="title">
                <template v-slot:body>
                    <FormDisplay :inputs="inputs" @onChange="onChange" />
                </template>
            </FormCard>
            <div class="mt-3">
                <b-button id="submit" variant="primary" class="mr-1" @click="handleSubmit">
                    {{ submitTitle }}
                </b-button>
            </div>
        </div>
    </div>
</template>
