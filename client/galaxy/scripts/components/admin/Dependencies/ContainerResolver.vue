<template>
    <span class="container-resolver">
        <span v-if="containerResolver" :title="title">
            {{ resolverType }}
            <span v-if="!compact">
                <i>{{ description }}</i>
            </span>
        </span>
        <span v-else-if="compact"> </span>
        <span v-else>
            <i>no container resolver</i>
        </span>
    </span>
</template>
<script>
export const DESCRIPTION = {
    explicit:
        "This explicit container resolver looks for containers annotated as part of the tool description - independent of tool requirements and Galaxy configuration.",
    mulled: "The mulled container resolver fetches pre-built Docker containers based on hashing a tool requirements.",
    mulled_singularity:
        "The mulled_singularity container resolver fetches pre-built Singularity containers based on hashing a tool requirements.",
    cached_mulled:
        "The cached_mulled container resolver finds mulled containers cached on the Galaxy server and discovered with `docker images`.",
    cached_mulled_singularity:
        "The cached_mulled_singularity container resolver finds mulled containers cached in a directory mounted by the Galaxy server.",
    build_mulled: "",
    build_mulled_cached: ""
};

export default {
    props: {
        containerResolver: {
            type: Object
        },
        compact: {
            type: Boolean,
            default: true
        }
    },
    computed: {
        title: function() {
            return this.compact ? this.description : "";
        },
        description: function() {
            const description = DESCRIPTION[this.resolverType] || `Container resolver of type ${this.resolverType}.`;
            return `${description}`;
        },
        resolverType: function() {
            return this.containerResolver && this.containerResolver.resolver_type;
        }
    }
};
</script>
