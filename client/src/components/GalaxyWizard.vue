<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faThumbsDown, faThumbsUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BSkeleton } from "bootstrap-vue";
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
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true, removeNewlinesAfterList: true });
/** On submit, query the server and put response in display box **/
async function submitQuery() {
    busy.value = true;
    if (query.value === "") {
        errorMessage.value = "There is no context to provide a response.";
        busy.value = false;
        return;
    }
    /**
     * Note: We are using a POST request here, which at the backend checks if a response exists
     * for the given job_id and returns it if it does. If it doesn't, it will create a new response.
     * Curious whether this is better done by using a separate GET and then a POST?
     * TODO: Remove this comment after discussion.
     */
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
    } else {
        queryResponse.value = data;
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
        <!-- <Heading v-if="props.view == 'wizard'" inline h2>Ask the wizard</Heading>
        <div :class="props.view == 'wizard' && 'mt-2'">
            <b-input
                v-if="props.query == ''"
                id="wizardinput"
                v-model="query"
                style="width: 100%"
                placeholder="What's the difference in fasta and fastq files?"
                @keyup.enter="submitQuery" /> -->
        <BAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <BButton v-else-if="!queryResponse" class="w-100" variant="info" :disabled="busy" @click="submitQuery">
            <span v-if="!busy"> Let our Help Wizard Figure it out! </span>
            <LoadingSpan v-else message="Thinking" />
        </BButton>
        <div :class="props.view == 'wizard' && 'mt-4'">
            <div v-if="busy">
                <BSkeleton animation="wave" width="85%" />
                <BSkeleton animation="wave" width="55%" />
                <BSkeleton animation="wave" width="70%" />
            </div>
            <!-- eslint-disable-next-line vue/no-v-html -->
            <div v-else class="chatResponse" v-html="renderMarkdown(queryResponse)" />

            <div v-if="queryResponse" class="feedback-buttons mt-2">
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
</style>
