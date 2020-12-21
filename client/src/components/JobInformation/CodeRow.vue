<template>
    <tr @click="toggleExpanded">
        <td>
            {{ codeLabel }}
            <span v-if="codeItem && !expanded"><i>(Click to expand)</i></span>
        </td>
        <td v-if="expanded">
            <pre class="code">{{ codeItem }}</pre>
        </td>
        <td v-else-if="codeItem">
            <pre class="code preview">{{ codeItem }}</pre>
        </td>
        <td v-else><i>empty</i></td>
    </tr>
</template>
<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";

Vue.use(BootstrapVue);

export default {
    props: {
        codeLabel: String,
        codeItem: String,
    },
    data() {
        return { expanded: false };
    },
    methods: {
        toggleExpanded() {
            if (this.codeItem) {
                this.expanded = !this.expanded;
            }
        },
    },
};
</script>
