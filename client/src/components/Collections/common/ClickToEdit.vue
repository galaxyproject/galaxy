<template>
    <input
        class="click-to-edit-input"
        v-if="editable"
        contenteditable
        v-model="element"
        @blur="
            $emit('renamed-element', element);
            editable = false
        "
        @keyup.enter="
            $emit('renamed-element', element);
            editable = false;
        "
    />
    <label v-else @click="editable = true">
        {{ element }}
    </label>
</template>

<script>
export default {
    props: {
        element: {
            required: true,
            type: String,
        },
        title: {
            required: false,
            type: String,
        },
    },
    data: function () {
        return {
            editable: false,
        };
    },
};
</script>

<style>
.click-to-edit-input {
    width: 600px;
}
</style>
