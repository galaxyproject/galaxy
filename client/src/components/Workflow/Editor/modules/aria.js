import $ from "jquery";
import ariaAlert from "utils/ariaAlert";
import Connector from "./connector";

export function ariaSelectOutputNode(options) {
    const { e, manager, outputTerminal, outputEl } = options;
    const inputChoicesMenu = document.createElement("ul");
    const switchActiveItem = (currentActive, newActive) => {
        newActive.classList.add("active");
        newActive.focus();
        currentActive.classList.remove("active");
    };
    const removeMenu = () => {
        inputChoicesMenu.remove();
        outputEl.removeAttribute("aria-owns");
        outputEl.setAttribute("aria-grabbed", "false");
        outputEl.focus();
    };
    const inputChoiceKeyDown = (e) => {
        e.stopPropagation();
        const currentItem = e.currentTarget;
        const previousItem = currentItem.previousSibling;
        const nextItem = currentItem.nextSibling;
        const inputNodeKey = currentItem.getAttribute("node-key");
        const inputTerminalKey = currentItem.getAttribute("input-key");
        const inputTerminal = manager.nodes[inputNodeKey].inputTerminals[inputTerminalKey];
        let foundConnection = false;
        switch (e.keyCode) {
            // Arrow Down
            case 40:
                if (nextItem) {
                    switchActiveItem(currentItem, nextItem);
                } else {
                    switchActiveItem(currentItem, currentItem.parentNode.firstChild);
                }
                break;
            // Arrow Up
            case 38:
                if (previousItem) {
                    switchActiveItem(currentItem, previousItem);
                } else {
                    switchActiveItem(currentItem, currentItem.parentNode.lastChild);
                }
                break;
            // Space
            case 32:
                removeMenu();
                outputTerminal.connectors.forEach((x) => {
                    if (x.inputHandle === inputTerminal) {
                        x.destroy();
                        foundConnection = true;
                        ariaAlert("Connection destroyed");
                    }
                });
                if (!foundConnection) {
                    new Connector(manager.canvasManager, outputTerminal, inputTerminal).redraw();
                    ariaAlert("Node connected");
                }
                break;
        }
    };
    const buildMenu = () => {
        $(inputChoicesMenu).focusout((e) => {
            /* focus is still inside child element of menu so don't hide */
            if (!inputChoicesMenu.contains(e.relatedTarget)) {
                $(inputChoicesMenu).hide();
            }
        });
        inputChoicesMenu.id = "input-choices-menu";
        inputChoicesMenu.className = "list-group";
        inputChoicesMenu.style.position = "absolute";
        inputChoicesMenu.setAttribute("role", "menu");
        outputEl.setAttribute("aria-grabbed", "true");
        outputEl.setAttribute("aria-owns", "input-choices-menu");
        Object.entries(manager.nodes).forEach(([inputNodeKey, inputNode]) => {
            Object.entries(inputNode.inputTerminals).forEach(([inputTerminalKey, inputTerminal]) => {
                const connectionAcceptable = inputTerminal.canAccept(outputTerminal);
                let foundConnection = false;
                outputTerminal.connectors.forEach((x) => {
                    if (x.inputHandle === inputTerminal) {
                        foundConnection = true;
                    }
                });
                if (connectionAcceptable.canAccept || foundConnection) {
                    const inputChoiceItem = document.createElement("li");
                    inputChoiceItem.textContent = `${inputTerminal.name} in ${inputTerminal.node.name} node`;
                    inputChoiceItem.tabIndex = -1;
                    inputChoiceItem.onkeydown = inputChoiceKeyDown;
                    inputChoiceItem.className = "list-group-item";
                    inputChoiceItem.setAttribute("role", "menuitem");
                    inputChoiceItem.setAttribute("input-key", inputTerminalKey);
                    inputChoiceItem.setAttribute("node-key", inputNodeKey);
                    inputChoicesMenu.appendChild(inputChoiceItem);
                }
            });
        });
        if (inputChoicesMenu.firstChild) {
            outputEl.appendChild(inputChoicesMenu);
            inputChoicesMenu.firstChild.classList.add("active");
            inputChoicesMenu.firstChild.focus();
        } else {
            ariaAlert("There are no available inputs for this selected output");
        }
    };
    // Space
    if (e.keyCode === 32) {
        ariaAlert("Node selected");
        buildMenu();
    }
}
