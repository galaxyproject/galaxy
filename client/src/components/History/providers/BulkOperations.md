This module executes operations against a dynamioc selection of content from the current history.
The idea is that the user will not have to explicitly select every single piece of content from the
client.





operations() {
    return ;
},

toggleItemSelect(val) {
    if (!val) {
        this.$emit("resetSelection");
    }
    this.$emit("update:useItemSelection", val);
},



<!--
<b-modal id="show-hidden-content" title="Show Hidden Datasets" title-tag="h2" @ok="unhideAll">
    <p>{{ "Really unhide all hidden datasets?" | localize }}</p>
</b-modal>
<b-modal id="delete-hidden-content" title="Delete Hidden Datasets" title-tag="h2" @ok="deleteAllHidden">
    <p>{{ "Really delete all hidden datasets?" | localize }}</p>
</b-modal>
<b-modal id="purge-deleted-content" title="Purge Deleted Datasets" title-tag="h2" @ok="purgeAllDeleted">
    <p>{{ "Really delete all deleted datasets permanently? This cannot be undone." | localize }}</p>
</b-modal>
-->

<!--

// hideSelectedContent,
// unhideSelectedContent,
// deleteSelectedContent,
// undeleteSelectedContent,
// purgeSelectedContent,
import { createDatasetCollection } from "./model/queries";
import { cacheContent } from "./caching";
import { buildCollectionModal } from "./adapters/buildCollectionModal";


// #region Selected content manipulation, hide/show/delete/purge

// hideSelected() {
//     this.runOnSelection(hideSelectedContent);
// },
// unhideSelected() {
//     this.runOnSelection(unhideSelectedContent);
// },
// deleteSelected() {
//     this.runOnSelection(deleteSelectedContent);
// },
// undeleteSelected() {
//     this.runOnSelection(undeleteSelectedContent);
// },
// purgeSelected() {
//     this.runOnSelection(purgeSelectedContent);
// },
// async runOnSelection(fn) {
//     const items = Array.from(this.contentSelection.values());
//     const type_ids = items.map((o) => o.type_id);
//     await fn(this.history, type_ids);
//     this.$emit("resetSelection");
//     this.$emit("manualReload");
// },

// #endregion

// #region collection creation, fires up a modal

async buildDatasetList() {
    await this.buildNewCollection("list");
},
async buildDatasetPair() {
    await this.buildNewCollection("paired");
},
async buildListOfPairs() {
    await this.buildNewCollection("list:paired");
},
async buildCollectionFromRules() {
    await this.buildNewCollection("rules");
},
async buildNewCollection(collectionTypeCode) {
    const modalResult = await buildCollectionModal(collectionTypeCode, this.history.id, this.contentSelection);
    const newCollection = await createDatasetCollection(this.history, modalResult);
    await cacheContent(newCollection);
    this.$emit("manualReload");
},

// #endregion

<!--
<PriorityMenuItem
    key="copy-datasets"
    title="Copy Datasets"
    icon="fas fa-copy"
    @click="iframeRedirect('/dataset/copy_datasets')"
/>
-->