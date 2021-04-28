<template>
    <textarea v-if="area" class="ui-input" v-model="currentValue" @input="onChange" @change="onChange" />
    <input v-else class="ui-input" v-model="currentValue" @input="onChange" @change="onChange" />
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
            default: "",
        },
        area: {
            type: Boolean,
            default: false,
        },
    },
    watch: {
        value(newValue) {
            this.currentValue = newValue;
        },
    },
    data() {
        return {
            currentValue: this.value,
        };
    },
    methods: {
        onChange() {
            this.$emit("onChange", this.currentValue);
        },
    },
};
</script>
