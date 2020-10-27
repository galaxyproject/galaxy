<template>
    <div class="pair-collection-creator">
        <collection-creator
            :oncancel="oncancel"
            @hide-original-toggle="hideOriginalsToggle"
            @clicked-create="clickedCreate"
            :creationFn="creationFn"
        >
            <template v-slot:help-content>
                <p>
                    {{
                        l(
                            [
                                "Pair collections are permanent collections containing two datasets: one forward and one reverse. ",
                                "Often these are forward and reverse reads. The pair collections can be passed to tools and workflows in ",
                                "order to have analyses done on both datasets. This interface allows you to create a pair, name it, and ",
                                "swap which is forward and which reverse.",
                            ].join("")
                        )
                    }}
                </p>
                <ul>
                    <li>
                        {{ l("Click the ") }}
                        <i data-target=".swap">
                            {{ l("Swap") }}
                        </i>
                        {{ l("link to make your forward dataset the reverse and the reverse dataset forward") }}
                    </li>
                    <li>
                        {{ l("Click the ") }}
                        <i data-target=".cancel-create">
                            {{ l("Cancel") }}
                        </i>
                        {{ l("button to exit the interface.") }}
                    </li>
                </ul>
                <br />
                <p>
                    {{ l("Once your collection is complete, enter a ") }}
                    <i data-target=".collection-name"> {{ l("name") }}</i>
                    {{ l("and click ") }}
                    <i data-target=".create-collection">
                        {{ l("Create list") }}
                    </i>
                    {{ l(".") }}
                </p>
            </template>
            <template v-slot:middle-content>
                <div class="collection-elements-controls">
                    <a class="swap" href="javascript:void(0);" title="l('Swap forward and reverse datasets')">
                        {{ l("Swap") }}
                    </a>
                </div>
                <div class="collection-elements scroll-container flex-row"></div>
            </template>
        </collection-creator>
    </div>
</template>

<script>
import CollectionCreator from "./common/CollectionCreator";
export default {
    components: { CollectionCreator },
    methods: {
        l(str) {
            // _l conflicts private methods of Vue internals, expose as l instead
            return _l(str);
        },
    },
};
</script>
