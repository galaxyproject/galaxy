<template>
    <b-row>
        <b-col sm="1">
            <b-form-input class="cursor-pointer" :id="id" v-model="currentValue" type="color" size="sm" />
        </b-col>
        <b-col class="pl-0">
            <label class="pt-1 cursor-pointer" :for="id">Select a color</label>
        </b-col>
    </b-row>
</template>

<script>
export default {
    props: {
        value: {
            type: String,
            required: true,
        },
        id: {
            type: String,
            required: true,
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
<style scoped>
@import "utils/pointer.css";
</style>
