<template>
    <div>
        <header class="main-header">
            <h1 class="text-center my-3">{{ title }}</h1>
            <h4 class="text-center my-3">{{ subtitle }}</h4>
        </header>
    </div>
</template>

<script>
import _l from "utils/localization";

export default {
    props: {
        userId: {
            type: String,
            required: true,
        },
        quotasEnabled: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        return {
            title: _l("Storage Dashboard"),
            subtitle: _l("Here you can see an overview of your disk usage status."),
        };
    },
};
</script>
