<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBug } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCollapse, BLink } from "bootstrap-vue";
import { computed, ref } from "vue";

import { dispatchReport, type ReportType } from "@/components/Collections/common/reporting";
import { useMarkdown } from "@/composables/markdown";
import localize from "@/utils/localization";

import FormElement from "@/components/Form/FormElement.vue";

library.add(faBug);

interface Props {
    reportType: ReportType;
    reportableData: object;
    reportingEmail: string;
}

const props = defineProps<Props>();
const { renderMarkdown } = useMarkdown({ openLinksInNewPage: true });
const message = ref("");
const errorMessage = ref("");
const resultMessages = ref<string[][]>([]);
const isExpanded = ref(<boolean>false);
const showForm = computed(() => {
    const noResult = !resultMessages.value.length;
    const hasError = resultMessages.value.some((msg) => msg[1] === "danger");
    return noResult || hasError;
});
const FIELD_MESSAGE = {
    loginRequired: localize("You must be logged in to send emails."),
    dataRequired: localize("You must provide a valid object to send emails."),
};
const fieldMessages = computed(() =>
    [!props.reportableData && FIELD_MESSAGE.dataRequired, !props.reportingEmail && FIELD_MESSAGE.loginRequired].filter(
        Boolean
    )
);
const expandedIcon = computed(() => (isExpanded.value ? "-" : "+"));

async function handleSubmit(reportType: ReportType, data?: any, email?: string | null) {
    if (!data || !email) {
        return;
    }

    const { messages, error } = await dispatchReport(reportType, data, message.value, email);

    if (error) {
        errorMessage.value = error;
    } else {
        resultMessages.value = messages;
    }
}
</script>

<template>
    <div>
        <BAlert v-for="(resultMessage, index) in resultMessages" :key="index" :variant="resultMessage[1]" show>
            <span v-html="renderMarkdown(resultMessage[0])" />
        </BAlert>

        <div v-if="showForm" id="data-error-form">
            <div>
                <span class="mr-2 font-weight-bold">{{ localize("Your email address") }}</span>
                <span v-if="props.reportingEmail">{{ props.reportingEmail }}</span>
                <span v-else>{{ FIELD_MESSAGE.loginRequired }}</span>
            </div>
            <div>
                <span class="mr-2 font-weight-bold">{{
                    localize("Please provide detailed information on the activities leading to this issue:")
                }}</span>
                <span v-if="!props.reportableData">{{ FIELD_MESSAGE.dataRequired }}</span>
            </div>
            <FormElement v-if="props.reportableData" id="object-error-message" v-model="message" :area="true" />
            <BLink
                :aria-expanded="isExpanded ? 'true' : 'false'"
                aria-controls="collapse-previous"
                @click="isExpanded = !isExpanded">
                ({{ expandedIcon }}) Error transcript:
            </BLink>
            <BCollapse id="collapse-previous" v-model="isExpanded">
                <pre class="rounded code">{{ reportableData }}</pre>
            </BCollapse>
            <br />
            <BButton
                id="data-error-submit"
                v-b-tooltip.hover
                :title="fieldMessages.join('\n')"
                variant="primary"
                class="mt-3"
                @click="handleSubmit(props.reportType, props.reportableData, props.reportingEmail)">
                <FontAwesomeIcon :icon="faBug" class="mr-1" />
                Report
            </BButton>
        </div>
    </div>
</template>
