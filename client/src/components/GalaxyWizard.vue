<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faThumbsDown, faThumbsUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton, BSkeleton } from "bootstrap-vue";
import { ref } from "vue";

import { GalaxyApi } from "@/api";
import { useMarkdown } from "@/composables/markdown";
import { errorMessageAsString } from "@/utils/simple-error";

import LoadingSpan from "./LoadingSpan.vue";

library.add(faThumbsUp, faThumbsDown);
interface Props {
    context?: string;
    jobId: string;
    query: string;
    view?: "wizard" | "error";
}
const props = withDefaults(defineProps<Props>(), {
    view: "error",
    context: "username",
});

const query = ref(props.query);
const queryResponse = ref("");
const errorMessage = ref("");
const busy = ref(false);
const feedback = ref<null | "up" | "down">(null);
const hasError = ref(false);
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });

/** On submit, query the server and put response in display box **/
async function submitQuery() {
    busy.value = true;
    hasError.value = false;
    errorMessage.value = "";
    queryResponse.value = "";

    if (query.value === "") {
        errorMessage.value = "There is no context to provide a response.";
        busy.value = false;
        return;
    }

    const { data, error } = await GalaxyApi().POST("/api/chat", {
        params: {
            query: { job_id: props.jobId },
        },
        body: {
            query: query.value,
            context: props.context,
        },
    });

    if (error) {
        errorMessage.value = errorMessageAsString(error, "Failed to get response from the server.");
        hasError.value = true;
    } else {
        if (data.response) {
            queryResponse.value = data.response;
        }

        // If there's an error code or message, set the error flag and message
        if (data.error_code || data.error_message) {
            hasError.value = true;

            if (data.error_code && data.error_message) {
                errorMessage.value = `${data.error_message} (Error ${data.error_code})`;
            } else if (data.error_message) {
                errorMessage.value = data.error_message;
            } else if (data.error_code) {
                errorMessage.value = `Error ${data.error_code}`;
            }
        }
    }

    busy.value = false;
}
/** Send feedback to the server **/
async function sendFeedback(value: "up" | "down") {
    feedback.value = value;
    // up is 1 and down is 0
    const feedbackValue = value === "up" ? 1 : 0;
    const { error } = await GalaxyApi().PUT("/api/chat/{job_id}/feedback", {
        params: {
            path: { job_id: props.jobId },
            query: { feedback: feedbackValue },
        },
    });
    if (error) {
        errorMessage.value = errorMessageAsString(error, "Failed to send feedback to the server.");
    }
}
</script>

<template>
    <div>
        <BButton v-if="!queryResponse" class="w-100" variant="info" :disabled="busy" @click="submitQuery">
            <span v-if="!busy"> Let our Help Wizard Figure it out! </span>
            <LoadingSpan v-else message="Thinking" />
        </BButton>
        <div :class="props.view == 'wizard' && 'mt-4'">
            <div v-if="busy">
                <BSkeleton animation="wave" width="85%" />
                <BSkeleton animation="wave" width="55%" />
                <BSkeleton animation="wave" width="70%" />
            </div>
            <div v-else>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <div class="chatResponse" v-html="renderMarkdown(queryResponse)" />

                <template v-if="errorMessage">
                    <hr class="error-divider" />
                    <div class="error-message">{{ errorMessage }}</div>
                </template>
            </div>

            <div v-if="queryResponse && !hasError" class="feedback-buttons mt-2">
                <hr class="w-100" />
                <h4>Was this answer helpful?</h4>
                <BButton
                    variant="success"
                    :disabled="feedback !== null"
                    :class="{ submitted: feedback === 'up' }"
                    @click="sendFeedback('up')">
                    <FontAwesomeIcon :icon="faThumbsUp" fixed-width />
                </BButton>
                <BButton
                    variant="danger"
                    :disabled="feedback !== null"
                    :class="{ submitted: feedback === 'down' }"
                    @click="sendFeedback('down')">
                    <FontAwesomeIcon :icon="faThumbsDown" fixed-width />
                </BButton>
                <i v-if="!feedback">This feedback helps us improve our responses.</i>
                <i v-else>Thank you for your feedback!</i>
            </div>
        </div>
    </div>
</template>
<style lang="scss" scoped>
.chatResponse {
    white-space: pre-wrap;
}
.submitted svg {
    animation: swoosh-up 1s forwards;
}
@keyframes swoosh-up {
    0% {
        transform: translateY(0);
    }
    50% {
        transform: translateY(-20px);
    }
    100% {
        transform: translateY(0);
    }
}

.error-divider {
    margin: 12px 0;
    border-top: 1px dashed #ccc;
}

.error-message {
    font-family: monospace;
    font-size: 12px;
    color: #d9534f;
    padding: 8px;
    background-color: #f9f2f2;
    border-radius: 3px;
}
</style>
