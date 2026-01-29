<template>
    <div>
        <label ref="helpTarget" v-b-tooltip.hover for="regular_expression">{{ label }}</label>
        <HelpPopover :target="$refs.helpTarget" term="programming.python.regex" />
        <input
            v-b-tooltip.hover.left
            :title="title"
            name="regular_expression"
            class="rule-regular-expression"
            type="text"
            :value="target"
            @input="$emit('update:target', $event.target.value)" />
    </div>
</template>

<script>
import _l from "utils/localization";

import HelpPopover from "@/components/Help/HelpPopover.vue";

export default {
    components: { HelpPopover },
    props: {
        target: {
            required: true,
        },
    },
    computed: {
        label() {
            return _l("Regular Expression");
        },
        title() {
            return _l("Enter a regular expression.");
        },
        popoverTitle() {
            return _l("Regular Expressions");
        },
    },
};
</script>
