<template>
    <div>
        <div v-if="error" class="alert alert-danger" show>{{ error }}</div>
        <div v-else>
            <slot name="header"></slot>
            <loading-span v-if="loading" :message="loadingMessage" />
            <div v-else>
                <slot name="actions"></slot>
                <slot name="body"></slot>
                <slot name="actions"></slot>
            </div>
        </div>
    </div>
</template>
<script>
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        LoadingSpan,
    },
    props: {
        loading: {
            type: Boolean,
            required: true,
        },
        loadingMessage: {
            type: String,
            required: true,
        },
        error: {
            type: String,
            default: null,
        },
    },
};
</script>
