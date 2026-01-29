<template>
    <span class="creative-work-creator">
        <OrganizationViewer v-if="creator.class == 'Organization'" :organization="creator">
            <template v-slot:buttons>
                <slot name="buttons"></slot>
            </template>
        </OrganizationViewer>
        <PersonViewer v-else :person="creator">
            <template v-slot:buttons>
                <slot name="buttons"></slot>
            </template>
        </PersonViewer>
    </span>
</template>

<script>
import OrganizationViewer from "./OrganizationViewer";
import PersonViewer from "./PersonViewer";

export default {
    components: {
        OrganizationViewer,
        PersonViewer,
    },
    props: {
        creator: {
            type: Object,
        },
    },
};
</script>
