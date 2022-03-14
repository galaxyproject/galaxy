from alembic import op


def drop_column(table, column):
    with op.batch_alter_table(table) as batch_op:
        batch_op.drop_column(column)
