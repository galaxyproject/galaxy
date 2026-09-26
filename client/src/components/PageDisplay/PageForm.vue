<template>
    <div>
        <BAlert v-if="loading" show>
            <LoadingSpan />
        </BAlert>
        <BAlert v-else-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
        <div v-else>
            <FormCard :title="cardTitle" icon="fa-file-contract">
                <template v-slot:body>
                    <FormElementLabel title="Title" :required="true" :condition="!!title">
                        <FormInput id="page-title" v-model="title" />
                    </FormElementLabel>
                    <FormElementLabel
                        title="Identifier"
                        :help="FORM_LABELS.slugHelp"
                        :required="true"
                        :condition="!!slug">
                        <FormInput id="page-slug" v-model="slug" />
                    </FormElementLabel>
                    <FormElementLabel title="Annotation" :help="FORM_LABELS.annotationHelp">
                        <FormInput id="page-annotation" v-model="annotation" />
                    </FormElementLabel>
                </template>
            </FormCard>
            <GButton
                id="page-submit"
                class="my-2"
                color="blue"
                :disabled="submitting || !title || !slug"
                :disabled-title="disabledTitle"
                @click="onSubmit">
                <FontAwesomeIcon :icon="submitting ? faSpinner : faSave" class="mr-1" :spin="submitting" />
                <span v-localize>{{ buttonText }}</span>
            </GButton>
        </div>
    </div>
</template>

<script setup lang="ts">
import { faSave, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { fetchInvocationReport } from "@/api/invocations";
import { FORM_LABELS } from "@/components/Page/constants";
import pageTemplate from "@/components/PageDisplay/pageTemplate.yml";
import { useToast } from "@/composables/toast";

import GButton from "@/components/BaseComponents/GButton.vue";
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
const submitting = ref(false);
const slug = ref("");
const title = ref("");

const disabledTitle = computed(() => {
    if (submitting.value) {
        return "Submitting";
    }
    if (!title.value || !slug.value) {
        return "Please complete all required inputs.";
    }
    return "";
});

const router = useRouter();

const Toast = useToast();

const cardTitle = props.mode === "edit" ? FORM_LABELS.editTitle : FORM_LABELS.createTitle;
const buttonText = props.mode === "edit" ? "Update" : "Create";

async function fetchData() {
    if (props.mode === "create" && props.invocationId) {
        try {
            loading.value = true;
            const data = await fetchInvocationReport(props.invocationId);
            errorMessage.value = "";
            content.value = data.invocation_markdown || "";
            slug.value = `invocation-${data.id}`;
            title.value = data.title;
        } catch (error) {
            errorMessage.value = error as string;
        } finally {
            loading.value = false;
        }
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
            slug.value = data.slug ?? "";
            title.value = data.title;
        }
        loading.value = false;
    }
}

async function onSubmit() {
    if (!slug.value || !title.value) {
        Toast.error("Please complete all required inputs.");
        return;
    }

    submitting.value = true;
    if (props.mode === "create") {
        const { data, error } = await GalaxyApi().POST("/api/pages", {
            body: {
                annotation: annotation.value,
                content: content.value,
                content_format: "markdown",
                slug: slug.value,
                title: title.value,
                ...(props.invocationId && { invocation_id: props.invocationId }),
            },
        });
        if (error) {
            Toast.error(error.err_msg, "Error Creating Page");
        } else if (data.history_id) {
            Toast.success("Galaxy Notebook created successfully");
            router.push(`/histories/${data.history_id}/pages/${data.id}`);
        } else {
            Toast.success("Report created successfully");
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
            Toast.error(error.err_msg, "Error Updating Page");
        } else {
            Toast.success("Page updated successfully");
            router.push("/pages/list");
        }
    }
    submitting.value = false;
}

watch(() => [props.id, props.invocationId], fetchData, { immediate: true });
</script>
