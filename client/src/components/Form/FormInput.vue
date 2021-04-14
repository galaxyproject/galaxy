<template>
    <input class="ui-input" :value="currentValue" @onChange="onChange" />
</template>
<script>

export default {
    props: {
        id: {
            type: String,
            required: true,
        },
        value: {
            type: String,
            default: ""
        }
    },
    data() {
        return { currentValue: value };
    },
    methods: {
        onChange(value) {
            this.$emit("onChange", value)
        }
    },
};
</script>
