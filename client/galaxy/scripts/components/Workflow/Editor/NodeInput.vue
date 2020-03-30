<template>
    <div class="form-row dataRow input-data-row">
        {{ label }}
        <div ref="terminal" class="terminal input-terminal"/>
    </div>
</template>

<script>
export default {
    props: {
        input: {
            type: Object,
            required: true,
        },
        manager: {
            type: Object,
            required: true,
        },
    },
    computed: {
        label() {
            return this.input.label || this.input.name;
        },
    }
};
</script>
