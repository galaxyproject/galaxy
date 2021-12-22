<template>
    <div>
        <div class="text-center">
            <b-alert show variant="warning" v-if="is_admin">
                You are logged in as an <strong>administrator</strong> therefore you can manage any folder on this
                Galaxy instance.
            </b-alert>
            <b-alert show variant="warning" v-else>
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
