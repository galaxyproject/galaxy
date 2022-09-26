<template>
    <div id="columns">
        <div id="center">
            <div class="center-container">
                <div class="center-panel" style="display: block">
                    <slot />
                </div>
            </div>
        </div>
        <div id="right">
            test
            {{ details }}
            <hr/>
        </div>
    </div>
</template>

<script>
export default {
    props: {
        details: {
            type: Object,
            default: () => ({}),
        },
    },
    computed: {
    },
};
</script>
