import _l from "utils/localization";
import { fetchDiscardedDatasets } from "./services";

export const categories = [
    {
        name: _l("Discarded Items"),
        providers: [
            {
                name: _l("Deleted datasets"),
                description: _l(
                    "Datasets that you have marked as deleted but that haven't been permanently deleted." +
                        " You can restore these datasets or you can permanently remove them to free some space"
                ),
                fetchItems: fetchDiscardedDatasets,
            },
        ],
    },
];
