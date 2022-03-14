from alembic import op


def drop_column(table, column):
    with op.batch_alter_table("workflow") as batch_op:
        batch_op.drop_column("source_metadata")
