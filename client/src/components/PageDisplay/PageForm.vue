<template>
    <div>
        <LoadingSpan v-if="loading" />
        <div v-else>
            <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
            <FormCard :title="cardTitle" icon="fa-file-contract">
                <template v-slot:body>
                    <FormElementLabel title="Title" :required="true" :condition="!!title">
                        <FormInput id="page-title" v-model="title" />
                    </FormElementLabel>
                    <FormElementLabel
                        title="Identifier"
                        help="A unique identifier that will be used for public links to this page. This field can only contain lowercase letters, numbers, and dashes (-)."
                        :required="true"
                        :condition="!!slug">
                        <FormInput id="page-slug" v-model="slug" />
                    </FormElementLabel>
                    <FormElementLabel
                        title="Annotation"
                        help="A description of the page. The annotation is shown alongside published pages.">
                        <FormInput id="page-annotation" v-model="annotation" />
                    </FormElementLabel>
                </template>
            </FormCard>
            <BButton id="page-submit" class="my-2" variant="primary" @click="onSubmit">
                <FontAwesomeIcon :icon="faSave" class="mr-1" />
                <span v-localize>{{ buttonText }}</span>
            </BButton>
        </div>
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

import FormInput from "@/components/Form/Elements/FormInput.vue";
import FormCard from "@/components/Form/FormCard.vue";
import FormElementLabel from "@/components/Form/FormElementLabel.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const props = defineProps<{
    mode: "create" | "edit";
    id?: string;
    invocationId?: string;
}>();

const annotation = ref("");
const content = ref(pageTemplate.content);
const errorMessage = ref("");
const loading = ref(false);
const slug = ref("");
const title = ref("");

const router = useRouter();

const cardTitle = props.mode === "edit" ? "Edit Page" : "Create a new Page";
const buttonText = props.mode === "edit" ? "Update" : "Create";

async function fetchData() {
    if (props.mode === "create" && props.invocationId) {
        loading.value = true;
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
        loading.value = false;
    } else if (props.mode === "edit" && props.id) {
        loading.value = true;
        const { data, error } = await GalaxyApi().GET("/api/pages/{id}", {
            params: { path: { id: props.id } },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        } else {
            errorMessage.value = "";
            annotation.value = data.annotation || "";
            content.value = data.content;
            slug.value = data.slug;
            title.value = data.title;
        }
        loading.value = false;
    }
}

async function onSubmit() {
    if (!slug.value || !title.value) {
        errorMessage.value = "Please complete all required inputs.";
        return;
    }

    if (props.mode === "create") {
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
        const { error } = await GalaxyApi().PUT("/api/pages/{id}", {
            params: { path: { id: props.id! } },
            body: {
                annotation: annotation.value,
                slug: slug.value,
                title: title.value,
            },
        });
        if (error) {
            errorMessage.value = error.err_msg;
        } else {
            router.push("/pages/list");
        }
    }
}

watch(() => [props.id, props.invocationId], fetchData, { immediate: true });
</script>
