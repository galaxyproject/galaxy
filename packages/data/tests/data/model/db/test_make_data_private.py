import pytest
from sqlalchemy import select

from galaxy import model as m
from galaxy.model.scripts.make_data_private import (
    ACCESS,
    MANAGE,
    run,
)
from galaxy.security.idencoding import IdEncodingHelper

SECURITY = IdEncodingHelper(id_secret="secret")


@pytest.fixture
def make_history(make_history):
    def f(user, **attributes):
        history = make_history()
        history.user = user
        for name, value in attributes.items():
            setattr(history, name, value)
        return history

    return f


@pytest.fixture
def make_owned_hda(session, make_history, make_hda):
    def f(history=None, user=None, **kwd):
        history = history or make_history(user=user)
        return make_hda(history=history, create_dataset=True, sa_session=session, **kwd)

    return f


def dataset_permissions(session, hda):
    stmt = select(m.DatasetPermissions.action, m.DatasetPermissions.role_id).where(
        m.DatasetPermissions.dataset_id == hda.dataset.id
    )
    return set(session.execute(stmt).all())


def default_permissions(session, model_class, **filter_by):
    stmt = select(model_class.action, model_class.role_id).filter_by(**filter_by)
    return set(session.execute(stmt).all())


def test_restricts_datasets_only_their_owner_can_reach(
    session,
    engine,
    make_user_and_role,
    make_history,
    make_owned_hda,
    make_role,
    make_dataset_permissions,
    make_history_user_share_association,
    make_ldda,
    make_dataset_collection,
    make_dataset_collection_element,
    make_hdca,
):
    owner, owner_role = make_user_and_role()
    other, _ = make_user_and_role()
    private_history = make_history(user=owner)

    restrict = make_owned_hda(history=private_history)
    restrict_keeps_manage = make_owned_hda(history=private_history)
    make_dataset_permissions(action=MANAGE, dataset=restrict_keeps_manage.dataset, role=owner_role)
    in_purged_history = make_owned_hda(history=make_history(user=owner, deleted=True, purged=True))

    unchanged = {
        "published": make_owned_hda(history=make_history(user=owner, published=True)),
        "importable": make_owned_hda(history=make_history(user=owner, importable=True)),
        "anonymous": make_owned_hda(history=make_history(user=None)),
        "already_restricted": make_owned_hda(history=private_history),
        "purged": make_owned_hda(history=private_history),
        "library": make_owned_hda(history=private_history),
        "copied_to_other_user": make_owned_hda(history=private_history),
        "copied_to_anonymous_history": make_owned_hda(history=private_history),
        "in_shared_collection": make_owned_hda(history=private_history),
    }
    shared_history = make_history(user=owner)
    make_history_user_share_association(history=shared_history, user=other)
    unchanged["shared_with_user"] = make_owned_hda(history=shared_history)
    make_dataset_permissions(action=ACCESS, dataset=unchanged["already_restricted"].dataset, role=make_role())
    unchanged["purged"].dataset.purged = True
    make_ldda(dataset=unchanged["library"].dataset)
    make_owned_hda(history=make_history(user=other), dataset=unchanged["copied_to_other_user"].dataset)
    make_owned_hda(history=make_history(user=None), dataset=unchanged["copied_to_anonymous_history"].dataset)
    # A nested collection with an element in the private history, used from a published history.
    inner = make_dataset_collection(collection_type="list")
    make_dataset_collection_element(collection=inner, element=unchanged["in_shared_collection"], element_identifier="a")
    outer = make_dataset_collection(collection_type="list:list")
    make_dataset_collection_element(collection=outer, element=inner, element_identifier="b")
    make_hdca(collection=outer, history=make_history(user=owner, published=True))
    session.commit()
    before = {name: dataset_permissions(session, hda) for name, hda in unchanged.items()}

    counts = run(engine, commit=True, batch_size=2)

    assert dataset_permissions(session, restrict) == {(ACCESS, owner_role.id), (MANAGE, owner_role.id)}
    assert dataset_permissions(session, restrict_keeps_manage) == {(ACCESS, owner_role.id), (MANAGE, owner_role.id)}
    assert dataset_permissions(session, in_purged_history) == {(ACCESS, owner_role.id), (MANAGE, owner_role.id)}
    for name, hda in unchanged.items():
        assert dataset_permissions(session, hda) == before[name], name
    assert counts["dataset_permissions"] == 5


@pytest.mark.parametrize(
    "content",
    [
        "```galaxy\nhistory_dataset_display(history_dataset_id={hda_id})\n```",
        "```galaxy\nhistory_link(history_id={history_id})\n```",
        '<div class="embedded-item dataset placeholder" id="HistoryDatasetAssociation-{hda_id}"></div>',
        '<div class="embedded-item history placeholder" id="History-{history_id}"></div>',
        '<div class="embedded-item history placeholder" id="History-{encoded_history_id}"></div>',
        "```galaxy\njob_parameters(job_id={job_id})\n```",
        "```galaxy\ntool_stdout(implicit_collection_jobs_id={implicit_collection_jobs_id})\n```",
    ],
)
def test_leaves_histories_referenced_by_published_pages(
    session, engine, make_user_and_role, make_owned_hda, make_page, content
):
    owner, _ = make_user_and_role()
    referenced = make_owned_hda(user=owner)
    other_hda_in_history = make_owned_hda(history=referenced.history)
    page = make_page(user=owner, published=True)
    revision = m.PageRevision()
    revision.page = page
    job = m.Job()
    job.history = referenced.history
    implicit_collection_jobs = m.ImplicitCollectionJobs()
    session.add_all([job, implicit_collection_jobs])
    session.flush()
    session.add(
        m.ImplicitCollectionJobsJobAssociation(
            implicit_collection_jobs=implicit_collection_jobs, job=job, order_index=0
        )
    )
    revision.content = content.format(
        hda_id=referenced.id,
        history_id=referenced.history.id,
        encoded_history_id=SECURITY.encode_id(referenced.history.id),
        job_id=job.id,
        implicit_collection_jobs_id=implicit_collection_jobs.id,
    )
    session.add(revision)
    session.flush()
    page.latest_revision = revision
    unpublished_page = make_page(user=owner)
    unpublished_page.history = make_owned_hda(user=owner).history
    session.commit()

    counts = run(engine, commit=True, decode_id=SECURITY.decode_id)

    assert dataset_permissions(session, referenced) == set()
    assert dataset_permissions(session, other_hda_in_history) == set()
    assert counts["dataset_permissions"] == 2


def test_sets_default_permissions(
    session,
    engine,
    make_user_and_role,
    make_history,
    make_role,
    make_default_user_permissions,
    make_default_history_permissions,
    make_history_user_share_association,
):
    no_defaults, no_defaults_role = make_user_and_role()
    public_default, public_default_role = make_user_and_role()
    make_default_user_permissions(user=public_default, action=MANAGE, role=public_default_role)
    group_role = make_role()
    restricted_default, restricted_default_role = make_user_and_role()
    make_default_user_permissions(user=restricted_default, action=MANAGE, role=restricted_default_role)
    make_default_user_permissions(user=restricted_default, action=ACCESS, role=group_role)

    private_history = make_history(user=public_default)
    make_default_history_permissions(history=private_history, action=MANAGE, role=public_default_role)
    published_history = make_history(user=public_default, published=True)
    make_default_history_permissions(history=published_history, action=MANAGE, role=public_default_role)
    shared_history = make_history(user=public_default)
    make_default_history_permissions(history=shared_history, action=MANAGE, role=public_default_role)
    make_history_user_share_association(history=shared_history, user=no_defaults)
    session.commit()

    run(engine, commit=True)

    def user_defaults(user):
        return default_permissions(session, m.DefaultUserPermissions, user_id=user.id)

    def history_defaults(history):
        return default_permissions(session, m.DefaultHistoryPermissions, history_id=history.id)

    assert user_defaults(no_defaults) == {(MANAGE, no_defaults_role.id), (ACCESS, no_defaults_role.id)}
    assert user_defaults(public_default) == {(MANAGE, public_default_role.id), (ACCESS, public_default_role.id)}
    assert user_defaults(restricted_default) == {(MANAGE, restricted_default_role.id), (ACCESS, group_role.id)}
    assert history_defaults(private_history) == {(MANAGE, public_default_role.id), (ACCESS, public_default_role.id)}
    assert history_defaults(published_history) == {(MANAGE, public_default_role.id)}
    assert history_defaults(shared_history) == {(MANAGE, public_default_role.id)}


def test_dry_run_changes_nothing(session, engine, make_user_and_role, make_owned_hda):
    owner, _ = make_user_and_role()
    hda = make_owned_hda(user=owner)
    session.commit()

    counts = run(engine)

    assert counts == {"default_user_permissions": 2, "default_history_permissions": 2, "dataset_permissions": 2}
    assert dataset_permissions(session, hda) == set()
    assert default_permissions(session, m.DefaultUserPermissions, user_id=owner.id) == set()
    assert default_permissions(session, m.DefaultHistoryPermissions, history_id=hda.history.id) == set()


def test_converted_datasets_follow_the_datasets_they_were_converted_from(
    session, engine, make_user_and_role, make_history, make_owned_hda
):
    owner, owner_role = make_user_and_role()
    viewer, _ = make_user_and_role()

    def convert(parent, history):
        converted = make_owned_hda(history=history)
        session.add(m.ImplicitlyConvertedDatasetAssociation(parent=parent, dataset=converted, file_type="bigwig"))
        return converted

    private_parent = make_owned_hda(user=owner)
    converted_by_owner = convert(private_parent, make_history(user=owner))
    published_parent = make_owned_hda(history=make_history(user=owner, published=True))
    converted_by_viewer = convert(published_parent, make_history(user=viewer))
    converted_by_owner_from_published = convert(published_parent, make_history(user=owner))
    session.commit()

    run(engine, commit=True)

    private = {(ACCESS, owner_role.id), (MANAGE, owner_role.id)}
    assert dataset_permissions(session, private_parent) == private
    assert dataset_permissions(session, converted_by_owner) == private
    assert dataset_permissions(session, published_parent) == set()
    assert dataset_permissions(session, converted_by_viewer) == set()
    assert dataset_permissions(session, converted_by_owner_from_published) == set()
