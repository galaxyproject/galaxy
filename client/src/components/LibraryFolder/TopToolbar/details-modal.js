import { getGalaxyInstance } from "app";
import _l from "utils/localization";
import { Toast } from "ui/toast";
import mod_library_model from "mvc/library/library-model";
import _ from "underscore";

export function showLocInfo(metadata) {
    const lib_id = metadata.parent_library_id;
    const Galaxy = getGalaxyInstance();
    var library = null;
    if (Galaxy.libraries && Galaxy.libraries.libraryListView !== null) {
        library = Galaxy.libraries.libraryListView.collection.get(metadata.folder_id);
        showLocInfoModal(library);
    } else {
        library = new mod_library_model.Library({
            id: lib_id,
        });
        library.fetch({
            success: () => {
                showLocInfoModal(library, metadata);
            },
            error: function (model, response) {
                if (typeof response.responseJSON !== "undefined") {
                    Toast.error(response.responseJSON.err_msg);
                } else {
                    Toast.error("An error occurred.");
                }
            },
        });
    }
}

function showLocInfoModal(library, metadata) {
    const Galaxy = getGalaxyInstance();
    var template = templateLocInfoInModal();
    const modal = Galaxy.modal;
    modal.show({
        closing_events: true,
        title: _l("Location Details"),
        body: template({ library: library, options: metadata }),
        buttons: {
            Close: () => {
                Galaxy.modal.hide();
            },
        },
    });
}

function templateLocInfoInModal() {
    return _.template(
        `<div>
                <table class="grid table table-sm">
                    <thead>
                        <th style="width: 25%;">Library</th>
                        <th></th>
                    </thead>
                    <tbody>
                        <tr>
                            <td>name</td>
                            <td><%- library.get("name") %></td>
                        </tr>
                        <% if(library.get("description") !== "") { %>
                            <tr>
                                <td>description</td>
                                <td><%- library.get("description") %></td>
                            </tr>
                        <% } %>
                        <% if(library.get("synopsis") !== "") { %>
                            <tr>
                                <td>synopsis</td>
                                <td><%- library.get("synopsis") %></td>
                            </tr>
                        <% } %>
                        <% if(library.get("create_time_pretty") !== "") { %>
                            <tr>
                                <td>created</td>
                                <td>
                                    <span title="<%- library.get("create_time") %>">
                                        <%- library.get("create_time_pretty") %>
                                    </span>
                                </td>
                            </tr>
                        <% } %>
                        <tr>
                            <td>id</td>
                            <td><%- library.get("id") %></td>
                        </tr>
                    </tbody>
                </table>
                <table class="grid table table-sm">
                    <thead>
                        <th style="width: 25%;">Folder</th>
                        <th></th>
                    </thead>
                    <tbody>
                        <tr>
                            <td>name</td>
                            <td><%- options.folder_name %></td>
                        </tr>
                        <% if(options.folder_description !== "") { %>
                            <tr>
                                <td>description</td>
                                <td><%- options.folder_description %></td>
                            </tr>
                        <% } %>
                        <tr>
                            <td>id</td>
                            <td><%- options.id %></td>
                        </tr>
                    </tbody>
                </table>
            </div>`
    );
}
