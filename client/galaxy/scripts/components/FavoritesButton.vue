<template>
    <a class="panel-header-button"
       @click="showFavorites"
       v-b-tooltip.hover title="Show favorites"
       href="javascript:void(0)">
        <span class="fa fa-star-o"></span>
    </a>
</template>

<script>
    import { VBTooltip } from 'bootstrap-vue'

    export default {
        name: "FavoritesButton",
        directives: {
            'v-b-tooltip': VBTooltip
        },
        methods: {
            showFavorites() {
                // FIXME: use Vue communication for this
                const toolSearchQueryNode = document.querySelector('.tool-search-query');
                toolSearchQueryNode.value = "#favorites";
                toolSearchQueryNode.dispatchEvent(new Event("input"));
            },
        }
    }
</script>

<style scoped>

</style>