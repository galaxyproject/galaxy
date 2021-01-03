<template>
    <b-modal v-model="show" title="Issues loading this workflow" scrollable ok-only ok-title="Continue">
        <div class="state-upgrade-modal">
            Please review the following issues, possibly resulting from tool upgrades or changes.
            <ul class="workflow-state-upgrade-step-summaries">
                <li v-for="(stateMessage, index) in stateMessages" :key="index">
                    <b>
                        <i :class="iconClass(stateMessage)" />
                        Step {{ humanIndex(stateMessage) }}: {{ title(stateMessage) }}
                    </b>
                    <ul class="workflow-state-upgrade-step-details">
                        <li v-for="(detail, detailIndex) in stateMessage.details" :key="detailIndex">
                            - <span v-html="detail" />
                        </li>
                    </ul>
                </li>
            </ul>
        </div>
    </b-modal>
</template>

<script>
import { BModal } from "bootstrap-vue";

export default {
    components: { BModal },
    props: {
        stateMessages: {
            type: Array,
            requierd: true,
        },
    },
    data() {
        return {
            show: this.stateMessages.length > 0,
        };
    },
    methods: {
        humanIndex(stateMessage) {
            return `${parseInt(stateMessage.stepIndex, 10) + 1}`;
        },
        title(stateMessage) {
            return stateMessage.label ? stateMessage.label : stateMessage.name;
        },
        iconClass(stateMessage) {
            let iconClassStr = "";
            if (stateMessage.iconType) {
                // stolen from Node.vue.
                iconClassStr = `icon fa fa-fw ${stateMessage.iconType}`;
            }
            return iconClassStr;
        },
    },
    watch: {
        stateMessages() {
            if (this.stateMessages.length > 0) {
                this.show = true;
            }
        },
    },
};
</script>

<style>
/* scoped styles not working because of modal, using long names instead. */
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
