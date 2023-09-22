<template>
    <li class="dataset-hash">
        <i>{{ hash.hash_value }}</i>
    </li>
</template>

<script>
export default {
    props: {
        hash: {
            type: Object,
            required: true,
        },
    },
};
</script>
