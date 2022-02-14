"""No-op cleanup for existing datasets."""


def upgrade(migrate_engine):
    print(__doc__)


def downgrade(migrate_engine):
    pass
