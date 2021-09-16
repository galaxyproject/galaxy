<template>
    <textarea v-if="area" :id="id" class="ui-textarea" v-model="currentValue" />
    <input v-else :id="id" class="ui-input" v-model="currentValue" />
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
