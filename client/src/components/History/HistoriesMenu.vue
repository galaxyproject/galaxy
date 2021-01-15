<template>
    <div>
        <PriorityMenu :starting-height="27">
            <PriorityMenuItem
                key="create-new-history"
                title="Create New History"
                icon="fa fa-plus"
                @click="$emit('createNewHistory')"
            />
            <PriorityMenuItem
                key="view-all-histories"
                title="View All Histories"
                icon="fa fa-columns"
                @click="redirect('/history/view_multiple')"
            />
            <PriorityMenuItem
                key="saved-histories"
                title="Saved Histories"
                icon="fas fa-save"
                @click="backboneRoute('/histories/list')"
            />
            <PriorityMenuItem
                key="clear-history-cache"
                title="Clear cache"
                icon="fa fa-refresh"
                @click.stop="clearCache"
            />
            <PriorityMenuItem
                key="use-legacy-history"
                title="Return to legacy history panel"
                icon="fas fa-exchange-alt"
                @click="switchToLegacyHistoryPanel"
            />
        </PriorityMenu>
    </div>
</template>

<script>
import { PriorityMenuItem, PriorityMenu } from "components/PriorityMenu";
import { wipeDatabase, clearHistoryDateStore } from "./caching";
import { legacyNavigationMixin } from "components/plugins";
import { switchToLegacyHistoryPanel } from "./adapters/betaToggle";

export default {
    mixins: [legacyNavigationMixin],
    components: {
        PriorityMenu,
        PriorityMenuItem,
    },
    methods: {
        async clearCache() {
            await wipeDatabase();
            await clearHistoryDateStore();
            location.reload();
        },
        switchToLegacyHistoryPanel,
    },
};
</script>
