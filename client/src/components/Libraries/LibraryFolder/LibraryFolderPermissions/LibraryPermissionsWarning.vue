<template>
    <div>
        <div class="text-center">
            <GAlert v-if="is_admin" show variant="warning">
                You are logged in as an <strong>administrator</strong> therefore you can manage any folder on this
                Galaxy instance.
            </GAlert>
            <GAlert v-else show variant="warning">
                You can assign any number of roles to any of the following permission types.
            </GAlert>
        </div>
    </div>
</template>

<script>
import GAlert from "@/component-library/GAlert.vue";

export default {
    components: {
        GAlert,
    },
    props: {
        is_admin: {
            type: Boolean,
            required: true,
        },
    },
};
</script>
