<template>
    <b-modal v-model="show" :title="title" scrollable ok-only ok-title="Continue">
        <div class="state-upgrade-modal">
            {{ message }}
            <ul class="workflow-state-upgrade-step-summaries">
                <li v-for="(stateMessage, index) in stateMessages" :key="index">
                    <b>
                        <i :class="iconClass(stateMessage)" />
                        Step {{ humanIndex(stateMessage) }}: {{ nodeTitle(stateMessage) }}
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
            required: true,
        },
        title: {
            type: String,
            default: "Issues loading this workflow",
        },
        message: {
            type: String,
            default: "Please review the following issues, possibly resulting from tool upgrades or changes.",
        },
    },
    data() {
        return {
            show: this.stateMessages.length > 0,
        };
    },
    watch: {
        stateMessages() {
            if (this.stateMessages.length > 0) {
                this.show = true;
            }
        },
    },
    methods: {
        humanIndex(stateMessage) {
            return `${parseInt(stateMessage.stepIndex, 10) + 1}`;
        },
        nodeTitle(stateMessage) {
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
