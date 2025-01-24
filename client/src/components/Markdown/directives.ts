import RAW_DIRECTIVE_DATA from "./directives.yml";

type DirectiveMode = "page" | "report";

type DirectiveMetadataValueByMode = {
    [key: string]: string;
};

interface DirectiveMetadata {
    side_panel_name: string | DirectiveMetadataValueByMode;
    side_panel_description?: string | DirectiveMetadataValueByMode;
    help?: string | DirectiveMetadataValueByMode;
}

type DirectivesMetadata = {
    [key: string]: DirectiveMetadata;
};

type SidePanelEntry = {
    [key: string]: string;
};

const DIRECTIVE_METADATA = RAW_DIRECTIVE_DATA as DirectivesMetadata;

export function directiveEntry(
    directiveId: string,
    mode: DirectiveMode,
    baseEntry: SidePanelEntry = {}
): SidePanelEntry {
    const directiveMetadataData: DirectiveMetadata | undefined = DIRECTIVE_METADATA[directiveId];
    if (directiveMetadataData == undefined) {
        throw Error(`Client logic error, cannot find directive metadata for ${directiveId}`);
    }
    let name = directiveMetadataData.side_panel_name;
    if (name && !(typeof name == "string")) {
        const modeName = name[mode];
        if (modeName == undefined) {
            throw Error(`Client logic error, cannot find directive metadata for ${directiveId}`);
        }
        name = modeName;
    }
    let description = directiveMetadataData.side_panel_description;
    if (description && !(typeof description == "string")) {
        description = description[mode];
    }
    let help = directiveMetadataData.help;
    if (help && !(typeof help == "string")) {
        help = help[mode];
    }
    if (help) {
        help = help.replace(/%MODE%/g, mode);
    }
    const entry: SidePanelEntry = { id: directiveId, ...baseEntry };
    if (name) {
        entry.name = name;
    }
    if (description) {
        entry.description = description;
    }
    if (help) {
        entry.help = help;
    }
    return entry;
}
