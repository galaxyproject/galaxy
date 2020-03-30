import $ from "jquery";
import ariaAlert from "utils/ariaAlert";
import Connector from "mvc/workflow/workflow-connector";

export function screenReaderSelectOutputNode(e, terminal) {
    const inputChoiceKeyDown = (e) => {
        e.stopPropagation();
        const currentItem = e.currentTarget;
        const previousItem = currentItem.previousSibling;
        const nextItem = currentItem.nextSibling;
        const inputTerminal = currentItem.input.context.terminal;
        const switchActiveItem = (currentActive, newActive) => {
            newActive.classList.add("active");
            newActive.focus();
            currentActive.classList.remove("active");
        };
        const removeMenu = () => {
            $(currentItem.parentNode).remove();
            terminal.$el.removeAttr("aria-owns");
            terminal.$el.attr("aria-grabbed", "false");
            terminal.$el.focus();
        };
        switch (e.keyCode) {
            case 40: // Down arrow
                if (nextItem) {
                    switchActiveItem(currentItem, nextItem);
                } else {
                    switchActiveItem(currentItem, currentItem.parentNode.firstChild);
                }
                break;
            case 38: // Up arrow
                if (previousItem) {
                    switchActiveItem(currentItem, previousItem);
                } else {
                    switchActiveItem(currentItem, currentItem.parentNode.lastChild);
                }
                break;
            case 32: // Space
                removeMenu();
                new Connector(terminal.app.canvas_manager, terminal, inputTerminal).redraw();
                ariaAlert("Node connected");
                if (inputTerminal.connectors.length > 0) {
                    const t = $("<div/>")
                        .addClass("delete-terminal")
                        .attr("tabindex", "0")
                        .attr("aria-label", "delete terminal")
                        .on("keydown click", (e) => {
                            if (e.keyCode === 32 || e.type === "click") {
                                //Space or Click
                                $.each(inputTerminal.connectors, (_, x) => {
                                    if (x) {
                                        x.destroy();
                                        ariaAlert("Connection destroyed");
                                    }
                                });
                                t.remove();
                            }
                        });
                    $(currentItem.input).parent().append(t);
                }
                break;
        }
    };
    const buildInputChoicesMenu = () => {
        const inputChoicesMenu = document.createElement("ul");
        $(inputChoicesMenu).focusout((e) => {
            /* focus is still inside child element of menu so don't hide */
            if (inputChoicesMenu.contains(e.relatedTarget)) {
                return;
            }
            $(inputChoicesMenu).hide();
        });
        inputChoicesMenu.id = "input-choices-menu";
        inputChoicesMenu.className = "list-group";
        inputChoicesMenu.setAttribute("role", "menu");
        terminal.$el.attr("aria-grabbed", "true");
        terminal.$el.attr("aria-owns", "input-choices-menu");
        $(".input-terminal").each((i, el) => {
            const input = $(el);
            const inputTerminal = input.context.terminal;
            const connectionAcceptable = inputTerminal.canAccept(terminal);
            if (connectionAcceptable.canAccept) {
                const inputChoiceItem = document.createElement("li");
                inputChoiceItem.textContent = `${inputTerminal.name} in ${inputTerminal.node.name} node`;
                inputChoiceItem.tabIndex = -1;
                inputChoiceItem.input = input;
                inputChoiceItem.onkeydown = inputChoiceKeyDown;
                inputChoiceItem.className = "list-group-item";
                inputChoiceItem.setAttribute("role", "menuitem");
                inputChoicesMenu.appendChild(inputChoiceItem);
            }
        });
        if (inputChoicesMenu.firstChild) {
            terminal.$el.append(inputChoicesMenu);
            inputChoicesMenu.firstChild.classList.add("active");
            inputChoicesMenu.firstChild.focus();
        } else {
            ariaAlert("There are no available inputs for this selected output");
        }
    };
    if (e.keyCode === 32) {
        // Space
        ariaAlert("Node selected");
        buildInputChoicesMenu();
    }
}
