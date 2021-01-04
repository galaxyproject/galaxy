import sqlalchemy as sa

metadata = sa.MetaData()

dataset = sa.Table(
    'dataset', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(40)),
)

# added in 2
history = sa.Table(
    'history', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('name', sa.String(40)),
)

hda = sa.Table(
    'hda', metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column("history_id", sa.Integer, sa.ForeignKey("history.id"), index=True),
    sa.Column("dataset_id", sa.Integer, sa.ForeignKey("dataset.id"), index=True),
    sa.Column('name', sa.String(40)),
)

# this table similates placing db under SA Migrate version control
migrate_version = sa.Table(
    'migrate_version', metadata,
    sa.Column('repository_id', sa.String(250), primary_key=True),
    sa.Column('repository_path', sa.Text),
    sa.Column('version', sa.Integer),
)


data = {
    'dataset': [
        (1, 'dataset1'),
        (2, 'dataset2'),
    ],
    'history': [
        (1, 'history1'),
        (2, 'history2'),
    ],
    'hda': [
        (1, 1, 1, 'hda1'),
        (2, 1, 2, 'hda2'),
        (3, 2, 1, 'hda3'),
    ],
    'migrate_version': [
        ('repo1', 'repo path', 1),
    ],
}
