import sqlalchemy as sa

metadata = sa.MetaData()

# 1. initialized, no versioning
dataset = sa.Table(
    'dataset', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(40)),
)


data = {
    'dataset': [
        (1, 'dataset1'),
        (2, 'dataset2'),
    ],
}
