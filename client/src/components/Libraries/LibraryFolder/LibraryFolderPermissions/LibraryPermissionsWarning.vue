<template>
    <div>
        <div class="text-center">
            <b-alert v-if="is_admin" show variant="warning">
                You are logged in as an <strong>administrator</strong> therefore you can manage any folder on this
                Galaxy instance.
            </b-alert>
            <b-alert v-else show variant="warning">
                You can assign any number of roles to any of the following permission types.
            </b-alert>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        is_admin: {
            type: Boolean,
            required: true,
        },
    },
};
</script>
