<script setup lang="ts">
import { faBug } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref } from "vue";

import { isRegisteredUser } from "@/api";
import { useMarkdown } from "@/composables/markdown";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import GButton from "../BaseComponents/GButton.vue";
import GLink from "../BaseComponents/GLink.vue";
import FormElement from "../Form/FormElement.vue";

const props = defineProps<{
    submit: (message: string) => Promise<string[][] | undefined>;
    requireLogin?: boolean;
}>();

const { currentUser } = storeToRefs(useUserStore());
const userEmail = computed<string | null>(() => {
    const user = currentUser.value;
    if (isRegisteredUser(user)) {
        return user.email;
    } else {
        return null;
    }
});

const message = ref("");
const resultMessages = ref<string[][]>([]);

const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });

const showForm = computed(() => {
    const noResult = !resultMessages.value.length;
    const hasError = resultMessages.value.some((msg) => msg[1] === "danger");

    return noResult || hasError;
});

async function submitEmail() {
    try {
        const messages = await props.submit(message.value);
        if (messages) {
            resultMessages.value = messages;
        }
    } catch (e) {
        const error = errorMessageAsString(e, localize("An error occurred while submitting the report."));
        resultMessages.value = [[localize(error), "danger"]];
    }
}
</script>

<template>
    <div>
        <h4 class="mb-3 h-md">Issue Report</h4>
        <BAlert v-if="props.requireLogin && !userEmail" variant="info" show>
            <span v-localize> You must be logged in to submit a report. </span>
            <GLink to="/login/start"> Please log in to continue. </GLink>
        </BAlert>

        <div v-else>
            <BAlert v-for="(resultMessage, index) in resultMessages" :key="index" :variant="resultMessage[1]" show>
                <!-- eslint-disable-next-line vue/no-v-html -->
                <span v-html="renderMarkdown(resultMessage[0] ?? '')" />
            </BAlert>

            <div v-if="showForm" id="email-report-form">
                <span class="mr-2 font-weight-bold">{{ localize("Your email address") }}</span>
                <span v-if="userEmail">{{ userEmail }}</span>
                <span v-else>{{ localize("You must be logged in to receive emails") }}</span>

                <FormElement
                    id="email-report-message"
                    v-model="message"
                    :area="true"
                    title="Please provide detailed information on the activities leading to the issue(s):" />

                <GButton id="email-report-submit" color="blue" class="mt-3" @click="submitEmail">
                    <FontAwesomeIcon :icon="faBug" class="mr-1" />
                    Report
                </GButton>
            </div>
        </div>
    </div>
</template>
