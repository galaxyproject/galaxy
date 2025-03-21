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
        errorMessage.value = "没有上下文，无法提供响应。";
        busy.value = false;
        return;
    }
    /**
     * 注意：这里我们使用的是 POST 请求，后端会检查是否已存在该 job_id 的响应，
     * 如果存在，则返回该响应；如果不存在，则创建一个新的响应。
     * 好奇是否更适合使用单独的 GET 进行检查，再使用 POST 发送请求？
     * TODO：讨论后删除此注释。
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
        errorMessage.value = errorMessageAsString(error, "无法从服务器获取响应。");
    } else {
        queryResponse.value = data;
    }
    busy.value = false;
}

/** 向服务器发送反馈 **/
async function sendFeedback(value: "up" | "down") {
    feedback.value = value;
    // “赞” 反馈值为 1，“踩” 反馈值为 0
    const feedbackValue = value === "up" ? 1 : 0;
    const { error } = await GalaxyApi().PUT("/api/chat/{job_id}/feedback", {
        params: {
            path: { job_id: props.jobId },
            query: { feedback: feedbackValue },
        },
    });
    if (error) {
        errorMessage.value = errorMessageAsString(error, "无法向服务器发送反馈。");
    }
}
</script>

<template>
    <div>
        <!-- <Heading v-if="props.view == 'wizard'" inline h2>请教向导</Heading>
        <div :class="props.view == 'wizard' && 'mt-2'">
            <b-input
                v-if="props.query == ''"
                id="wizardinput"
                v-model="query"
                style="width: 100%"
                placeholder="FASTA 文件和 FASTQ 文件有什么区别？"
                @keyup.enter="submitQuery" /> -->
        <BAlert v-if="errorMessage" variant="danger" show>
            {{ errorMessage }}
        </BAlert>
        <BButton v-else-if="!queryResponse" class="w-100" variant="info" :disabled="busy" @click="submitQuery">
            <span v-if="!busy"> 让我们的帮助向导来解答！ </span>
            <LoadingSpan v-else message="思考中..." />
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
                <h4>这个答案有帮助吗？</h4>
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
                <i v-if="!feedback">您的反馈有助于我们改进回答。</i>
                <i v-else>感谢您的反馈！</i>
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
