<template>
    <div v-if="ruleType == displayRuleType" class="rule-editor" :class="typeToClass">
        <slot></slot>
        <div class="buttons rule-edit-buttons d-flex justify-content-end">
            <button type="button" class="btn rule-editor-cancel mr-1" @click="cancel">{{ cancelLabel }}</button>
            <button type="button" class="btn btn-primary rule-editor-ok" @click="okay">{{ applyLabel }}</button>
        </div>
    </div>
</template>

<script>
import _l from "utils/localization";

export default {
    data: function () {
        return {
            applyLabel: _l("Apply"),
            cancelLabel: _l("Cancel"),
        };
    },
    props: {
        ruleType: {
            type: String,
            required: true,
        },
        displayRuleType: {
            required: true,
        },
        builder: {
            required: true,
        },
    },
    methods: {
        cancel() {
            this.$emit("update:displayRuleType", null);
        },
        okay() {
            this.builder.handleRuleSave(this.ruleType);
            this.cancel();
        },
    },
    computed: {
        typeToClass() {
            return "rule-edit-" + this.ruleType.replace(/_/g, "-");
        },
    },
};
</script>
