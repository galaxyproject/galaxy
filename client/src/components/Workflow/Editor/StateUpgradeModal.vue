<script setup lang="ts">
import { faCaretDown, faCaretUp } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import type { UpgradeMessage } from "./modules/utilities";

import GButton from "@/components/BaseComponents/GButton.vue";
import GCollapse from "@/components/BaseComponents/GCollapse.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

interface RenderedStateMessage extends UpgradeMessage {
    humanIndex: string;
    nodeTitle: string;
    iconClass: string;
}

interface Props {
    stateMessages: UpgradeMessage[];
    /** Parameters without a stored value that Galaxy filled with the tool's default: informational, not problems */
    filledDefaults?: UpgradeMessage[];
    title?: string;
    message?: string;
}

const emit = defineEmits<{
    /** The user accepted the filled defaults; the workflow now differs from what is stored */
    (e: "accept"): void;
}>();

const props = withDefaults(defineProps<Props>(), {
    filledDefaults: () => [],
    title: "Issues loading this workflow",
    message: "Please review the following issues, possibly resulting from tool upgrades or changes.",
});

const show = ref(props.stateMessages.length > 0 || props.filledDefaults.length > 0);
const showFilledDefaults = ref(false);

watch(
    () => [props.stateMessages, props.filledDefaults],
    () => {
        if (props.stateMessages.length > 0 || props.filledDefaults.length > 0) {
            show.value = true;
        }
    },
);

function render(messages: UpgradeMessage[]): RenderedStateMessage[] {
    return messages.map((stateMessage) => {
        const humanIndex = `${parseInt(stateMessage.stepIndex, 10) + 1}`;
        const nodeTitle = stateMessage.label ? stateMessage.label : stateMessage.name;
        let iconClass = "";
        if (stateMessage.iconType) {
            // TODO: stolen from Node.vue, so when modernizing that to use `IconDefinition`, fix this
            iconClass = `icon fa fa-fw ${stateMessage.iconType}`;
        }
        return {
            ...stateMessage,
            humanIndex,
            nodeTitle,
            iconClass,
        };
    });
}

const computedStateMessages = computed(() => render(props.stateMessages));
const computedFilledDefaults = computed(() => render(props.filledDefaults));
const filledDefaultCount = computed(() =>
    props.filledDefaults.reduce((count, message) => count + message.details.length, 0),
);
const filledDefaultsSummary = computed(() => {
    const values = filledDefaultCount.value === 1 ? "1 default value" : `${filledDefaultCount.value} default values`;
    const steps = props.filledDefaults.length === 1 ? "1 step" : `${props.filledDefaults.length} steps`;
    return `Galaxy filled in ${values} in ${steps}`;
});
const modalTitle = computed(() => (props.stateMessages.length > 0 ? props.title : "Default values filled in"));

// with issues listed too, "Accept" alone would read as accepting those as well
const okLabel = computed(() => {
    if (props.filledDefaults.length === 0) {
        return "OK";
    }
    return props.stateMessages.length > 0 ? "Accept defaults" : "Accept";
});

function onOk() {
    if (props.filledDefaults.length > 0) {
        emit("accept");
    }
    show.value = false;
}
</script>

<template>
    <GModal
        v-model:show="show"
        :title="modalTitle"
        size="medium"
        :fixed-height="computedStateMessages.length > 0 || showFilledDefaults"
        footer
        data-description="workflow state upgrade modal">
        <div v-if="show" data-description="workflow state upgrade modal content">
            <div v-if="computedStateMessages.length" data-description="workflow state upgrade review">
                {{ message }}
                <ul class="workflow-state-upgrade-step-summaries">
                    <li v-for="(stateMessage, index) in computedStateMessages" :key="index">
                        <b>
                            <i :class="stateMessage.iconClass" />
                            Step {{ stateMessage.humanIndex }}: {{ stateMessage.nodeTitle }}
                        </b>
                        <ul class="workflow-state-upgrade-step-details">
                            <li v-for="(detail, detailIndex) in stateMessage.details" :key="detailIndex">
                                <span v-sanitize-html:links="detail" />
                            </li>
                        </ul>
                    </li>
                </ul>
            </div>
            <div
                v-if="computedFilledDefaults.length"
                :class="{ 'mt-3': computedStateMessages.length }"
                data-description="workflow state upgrade filled defaults">
                <p class="mb-1">
                    {{ filledDefaultsSummary }}. The workflow gives these parameters no value, so Galaxy uses each
                    tool's default, as it does when the workflow runs. Accept them and save the workflow to store them,
                    so this note doesn't come back.
                </p>
                <GButton
                    v-model:pressed="showFilledDefaults"
                    :aria-pressed="showFilledDefaults ? 'true' : 'false'"
                    data-description="workflow state upgrade filled defaults toggle"
                    size="small"
                    color="blue"
                    transparent
                    inline>
                    {{ showFilledDefaults ? "Hide values" : "Show values" }}
                    <FontAwesomeIcon :icon="showFilledDefaults ? faCaretUp : faCaretDown" />
                </GButton>
                <GCollapse :visible="showFilledDefaults">
                    <ul class="workflow-state-upgrade-step-summaries">
                        <li v-for="(filled, index) in computedFilledDefaults" :key="index">
                            <b>
                                <i :class="filled.iconClass" />
                                Step {{ filled.humanIndex }}: {{ filled.nodeTitle }}
                            </b>
                            <ul class="workflow-state-upgrade-step-details">
                                <li v-for="(detail, detailIndex) in filled.details" :key="detailIndex">
                                    {{ detail }}
                                </li>
                            </ul>
                        </li>
                    </ul>
                </GCollapse>
            </div>
        </div>
        <template v-slot:footer>
            <GButton color="blue" data-description="workflow state upgrade modal ok" @click="onOk">
                {{ okLabel }}
            </GButton>
        </template>
    </GModal>
</template>

<style scoped>
ul.workflow-state-upgrade-step-summaries {
    margin-top: 10px;
    padding: 10px;
}
ul.workflow-state-upgrade-step-details {
    list-style-type: square !important;
}
ul.workflow-state-upgrade-step-details li {
    padding-left: 5px;
}
</style>
