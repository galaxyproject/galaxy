// Previously ran in masthead, moved into standard init

import Modal from "mvc/ui/ui-modal";

export function initModals(galaxy) {
    console.log("initModals");

    if (!galaxy.modal) {
        galaxy.modal = new Modal.View();
    }
}
