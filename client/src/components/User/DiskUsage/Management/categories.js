import _l from "utils/localization";
import { fetchDiscardedDatasets } from "./services";

export const categories = [
    {
        name: _l("Discarded Items"),
        providers: [
            {
                name: _l("Deleted datasets"),
                description: _l(
                    "When you delete a dataset it's not immediately removed from the disk (so you can recover it later)." +
                        " But this means it's still taking space until you permanently delete it." +
                        " Here you can quickly find and remove those datasets to free up some space"
                ),
                fetchItems: fetchDiscardedDatasets,
            },
        ],
    },
];
