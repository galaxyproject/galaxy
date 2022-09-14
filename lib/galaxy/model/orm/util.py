from sqlalchemy import inspect


def add_object_to_object_session(object, object_with_session):
    """
    Explicitly add object to the session.
    Addresses SQLAlchemy 2.0 compatibility issue:
    https://docs.sqlalchemy.org/en/14/changelog/migration_14.html#cascade-backrefs-behavior-deprecated-for-removal-in-2-0

    This function preserves SQLAlchemy's pre-2.0 logic and should be used when:

    1. foo and bar are model instances, that are associated (via SQLAlchemy's relationship), AND
    2. bar is assigned to foo's bar relationship (e.g. foo.bar = bar), AND
    3. bar is in a session and foo is not, AND
    4. foo is implicitly added to bar's session upon assignment(2), as indicated
       by a RemovedIn20Warning specifying that the '"foo" object is being merged into a Session
       along the backref cascade path...'
    """
    if object_with_session:
        session = get_object_session(object_with_session)
        if session:
            add_object_to_session(object, session)


def add_object_to_session(object, session):
    """Explicitly add object to the session."""
    if session and object:
        session.add(object)


def get_object_session(object):
    if object:
        return inspect(object).session
