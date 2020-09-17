<template>
    <collection-creator>
        <template v-slot:help-content>
            <p>
                {{
                    _l(
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
                    {{ _l(['Click the <i data-target=".swap">"Swap"</i> link to make your forward dataset the reverse '
                    'and the reverse dataset forward.'].join("")) }}
                </li>
                <li>{{_l('Click the <i data-target=".cancel-create">"Cancel"</i> button to exit the interface.')}}</li>
            </ul>
            <br />
            <p>
                {{ _l(['Once your collection is complete, enter a <i data-target=".collection-name">name</i> and click
                ', '<i data-target=".create-collection">"Create list"</i>.'].join("")) }}
            </p>
        </template>
        <template v-slot:middle-content>
            <div class="collection-elements-controls">
                <a class="swap" href="javascript:void(0);" title="_l('Swap forward and reverse datasets')">
                    {{ _l("Swap") }}
                </a>
            </div>
            <div class="collection-elements scroll-container flex-row"></div>
        </template>
    </collection-creator>
</template>
<script>
import CollectionCreatorMixin from "mvc/collection/mixins/CollectionCreatorMixin";
export default {};
</script>
