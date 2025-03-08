from tool_shed_client.schema import Category


def test_create_model():
    category = Category(
        id="1234567",
        name="my category",
        description="the description",
        deleted=False,
        repositories=3,
    )
    assert category.name == "my category"
