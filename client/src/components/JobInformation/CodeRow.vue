<template>
    <tr @click="expandCode">
        <td>
            {{ codeLabel }}
        </td>
        <td v-if="expanded">
            <pre class="code">{{ codeItem }}</pre>
        </td>
        <td v-else-if="codeItem">
            <pre class="code preview">{{ codeItem }}</pre>
            <b>(Click to expand)</b>
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
        expandCode() {
            if (this.codeItem) {
                this.expanded = true;
            }
        },
    },
};
</script>
