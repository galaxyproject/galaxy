<template>
    <LoadingSpan v-if="loadingReport" />
    <div v-else>
        <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <FormCard title="Create a new Page" icon="fa-file-contract">
            <template v-slot:body>
                <FormElementContainer title="Title" :required="true" :condition="!!title">
                    <FormInput id="title" v-model="title" />
                </FormElementContainer>
                <FormElementContainer
                    title="Identifier"
                    help="A unique identifier that will be used for public links to this page. This field can only contain lowercase letters, numbers, and dashes (-)."
                    :required="true"
                    :condition="!!slug">
                    <FormInput id="slug" v-model="slug" />
                </FormElementContainer>
                <FormElementContainer
                    title="Annotation"
                    help="A description of the page. The annotation is shown alongside published pages.">
                    <FormInput id="annotation" v-model="annotation" />
                </FormElementContainer>
            </template>
        </FormCard>
        <BButton class="my-2" variant="primary" @click="onCreate">
            <FontAwesomeIcon :icon="faSave" class="mr-1" />
            <span v-localize>Create</span>
        </BButton>
    </div>
</template>

<script setup lang="ts">
import { faSave } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton } from "bootstrap-vue";
import { ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import pageTemplate from "@/components/PageDisplay/pageTemplate.yml";

import FormElementContainer from "../Form/FormElementContainer.vue";
import FormInput from "@/components/Form/Elements/FormInput.vue";
import FormCard from "@/components/Form/FormCard.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const router = useRouter();

const props = defineProps<{
    invocationId?: string;
}>();

const annotation = ref("");
const content = ref(pageTemplate.content);
const errorMessage = ref("");
const loadingReport = ref(false);
const slug = ref("");
const title = ref("");

async function fetchReport() {
    if (props.invocationId) {
        loadingReport.value = true;
        const { data, error } = await GalaxyApi().GET("/api/invocations/{invocation_id}/report", {
            params: { path: { invocation_id: props.invocationId } },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        } else {
            errorMessage.value = "";
            content.value = data.invocation_markdown || "";
            slug.value = `invocation-${data.id}`;
            title.value = data.title;
        }
        loadingReport.value = false;
    }
}

async function onCreate() {
    if (slug.value && title.value) {
        const { data, error } = await GalaxyApi().POST("/api/pages", {
            body: {
                annotation: annotation.value,
                content: content.value,
                content_format: "markdown",
                slug: slug.value,
                title: title.value,
            },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        } else {
            router.push(`/pages/editor?id=${data.id}`);
        }
    } else {
        errorMessage.value = "Please complete all required inputs.";
    }
}

watch(
    () => props.invocationId,
    () => fetchReport(),
    { immediate: true }
);
</script>
