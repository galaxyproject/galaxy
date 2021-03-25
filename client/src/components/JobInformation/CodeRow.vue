<template>
    <tr @click="toggleExpanded">
        <td>
            {{ codeLabel }}
        </td>
        <td v-if="codeItem">
            <pre @click.stop :class="codeClass">{{ codeItem }}</pre>
            <i :class="iconClass" />
            <b>Click to {{ action }}</b>
        </td>
        <td v-else><i>empty</i></td>
    </tr>
</template>
<script>
export default {
    props: {
        codeLabel: String,
        codeItem: String,
    },
    data() {
        return { expanded: false };
    },
    computed: {
        action() {
            return this.expanded ? "collapse" : "expand";
        },
        codeClass() {
            return this.expanded ? "code" : "code preview";
        },
        iconClass() {
            return this.expanded ? "fa fa-minus" : "fa fa-plus";
        },
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
