<script setup lang="ts">
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowRun from "@/components/Workflow/Run/WorkflowRun.vue";

interface Props {
    uuid: string;
    secret?: string;
}

const props = withDefaults(defineProps<Props>(), {
    secret: undefined,
});

const workflowId = ref<string | null>(null);
const errorMessage = ref<string | null>(null);
const requestState = ref<Record<string, never> | null>(null);
const instance = ref<boolean>(false);
const userStore = useUserStore();
const router = useRouter();

userStore.loadUser(false);
const { isAnonymous, currentUser } = storeToRefs(userStore);

watch(
    currentUser,
    async () => {
        if (isAnonymous.value) {
            router.push(`/login/start?redirect=/workflow_landings/${props.uuid}`);
        } else if (currentUser.value) {
            const { data, error } = await GalaxyApi().GET("/api/workflow_landings/{uuid}", {
                params: {
                    path: { uuid: props.uuid },
                },
            });
            if (data) {
                workflowId.value = data.workflow_id;
                instance.value = data.workflow_target_type === "workflow";
                requestState.value = data.request_state;
            } else {
                errorMessage.value = errorMessageAsString(error);
            }
        }
    },
    { immediate: true }
);
</script>

<template>
    <div>
        <div v-if="errorMessage">
            <BAlert variant="danger" show>
                {{ errorMessage }}
            </BAlert>
        </div>
        <div v-else-if="!workflowId">
            <LoadingSpan message="Loading workflow parameters" />
        </div>
        <div v-else>
            <WorkflowRun
                :workflow-id="workflowId"
                :prefer-simple-form="true"
                :request-state="requestState"
                :instance="instance" />
        </div>
    </div>
</template>
