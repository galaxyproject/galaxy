<template>
    <textarea v-if="area" :id="id" v-model="currentValue" class="ui-textarea" />
    <input v-else :id="id" v-model="currentValue" class="ui-input" />
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
    computed: {
        currentValue: {
            get() {
                return this.value;
            },
            set(val) {
                this.$emit("input", val);
            },
        },
    },
};
</script>
