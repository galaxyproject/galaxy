import DirectoryPathEditableBreadcrumb from "components/FilesDialog/DirectoryPathEditableBreadcrumb";
import { waitForElementToBePresent } from "utils/utils";

import { mountVueComponent } from "utils/mountVueComponent";

export function breadcrump(selector, callback, options = {}) {
    waitForElementToBePresent(selector).then((selector) => {
        Object.assign(options, {
            callback: callback,
        });

        mountVueComponent(DirectoryPathEditableBreadcrumb)(options, selector);
    });
}
