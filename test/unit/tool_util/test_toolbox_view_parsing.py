import pydantic

from galaxy.tool_util.toolbox.views.definitions import (
    StaticToolBoxView,
    StaticToolBoxViewTypeEnum,
)

EXAMPLE_1 = {
    "id": "rna",
    "name": "RNA Seq",
    "type": "activity",
    "items": [
        {
            "type": "workflow",
            "id": "12345abcd",
        },
        {
            "type": "section",
            "name": "My Cool Section",
        },
        {
            "type": "label",
            "text": "My Cool Label",
            "id": "my-cool-label-id",
        },
        {
            "type": "tool",
            "id": "cat1",
        },
    ],
}


def test_root_parsing():
    view = StaticToolBoxView.from_dict(EXAMPLE_1)
    assert view.id == "rna"
    assert view.name == "RNA Seq"
    assert view.view_type == StaticToolBoxViewTypeEnum.activity
    assert len(view.items) == 4
    workflow_item = view.items[0]
    assert workflow_item.content_type == "workflow"
    assert workflow_item.id == "12345abcd"

    section_item = view.items[1]
    assert section_item.content_type == "section"
    assert section_item.id is None
    assert section_item.name == "My Cool Section"

    outer_label_item = view.items[2]
    assert outer_label_item.content_type == "label"
    assert outer_label_item.id == "my-cool-label-id"
    assert outer_label_item.text == "My Cool Label"

    output_tool_item = view.items[3]
    assert output_tool_item.content_type == "tool"
    assert output_tool_item.id == "cat1"


def test_section_parsing():
    view = StaticToolBoxView.from_dict(
        {
            "id": "rna",
            "name": "RNA Seq",
            "type": "activity",
            "items": [
                {
                    "type": "section",
                    "name": "My Cool Section",
                    "items": [
                        {
                            "type": "workflow",
                            "id": "123456",
                        }
                    ],
                },
            ],
        }
    )
    section_item = view.items[0]
    assert len(section_item.items) == 1
    assert section_item.items[0].content_type == "workflow"


def test_no_nested_sections():
    exception_raised = False
    try:
        StaticToolBoxView.from_dict(
            {
                "id": "rna",
                "name": "RNA Seq",
                "type": "activity",
                "items": [
                    {
                        "type": "section",
                        "name": "My Cool Section",
                        "items": [
                            {
                                "type": "section",
                                "name": "My Cool Inner Section",
                            },
                        ],
                    },
                ],
            }
        )
    except pydantic.ValidationError:
        exception_raised = True
    assert exception_raised
