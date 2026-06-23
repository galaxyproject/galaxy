<script setup lang="ts">
import { computed, ref, watch } from "vue";

import type { UpgradeMessage } from "./modules/utilities";

import GModal from "@/components/BaseComponents/GModal.vue";

interface RenderedStateMessage extends UpgradeMessage {
    humanIndex: string;
    nodeTitle: string;
    iconClass: string;
}

interface Props {
    stateMessages: UpgradeMessage[];
    title?: string;
    message?: string;
}

const props = withDefaults(defineProps<Props>(), {
    title: "Issues loading this workflow",
    message: "Please review the following issues, possibly resulting from tool upgrades or changes.",
});

const show = ref(props.stateMessages.length > 0);

watch(
    () => props.stateMessages,
    (newMessages) => {
        if (newMessages.length > 0) {
            show.value = true;
        }
    },
);

const computedStateMessages = computed<RenderedStateMessage[]>(() => {
    return props.stateMessages.map((stateMessage) => {
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
});
</script>

<template>
    <GModal :show.sync="show" :title="title" size="medium" fixed-height data-description="workflow state upgrade modal">
        <div v-if="show" data-description="workflow state upgrade modal content">
            {{ message }}
            <ul class="workflow-state-upgrade-step-summaries">
                <li v-for="(stateMessage, index) in computedStateMessages" :key="index">
                    <b>
                        <i :class="stateMessage.iconClass" />
                        Step {{ stateMessage.humanIndex }}: {{ stateMessage.nodeTitle }}
                    </b>
                    <ul class="workflow-state-upgrade-step-details">
                        <li v-for="(detail, detailIndex) in stateMessage.details" :key="detailIndex">
                            <!-- eslint-disable-next-line vue/no-v-html -->
                            <span v-html="detail" />
                        </li>
                    </ul>
                </li>
            </ul>
        </div>
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
