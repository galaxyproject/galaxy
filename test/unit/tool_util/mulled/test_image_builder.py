import contextlib
import os
import shutil
import tempfile

import pytest

from galaxy.tool_util.deps.mulled.image_builder import (
    DEFAULT_DESTINATION_IMAGE,
    DEFAULT_EXTENDED_BASE_IMAGE,
    DockerContainerBuilder,
    SingularityContainerBuilder,
)
from ..test_conda_resolution import external_dependency_management


@pytest.fixture(scope="module")
def artifcat_dir():
    tempdir = tempfile.mkdtemp(prefix="GALAXY_PYTEST_MULLED_")
    try:
        yield tempdir
    finally:
        shutil.rmtree(tempdir)


def test_build_stage1_info():
    repo = 'transtermhp'
    builder = DockerContainerBuilder(repo=repo, target_args=repo)
    info = builder.build_info(builder.template_stage1)
    build_command = info.build_command
    assert isinstance(build_command, list)
    assert build_command[0] == 'docker'
    assert build_command[1] == 'build'
    assert build_command[2] == '-t'
    assert build_command[3] == repo
    assert os.path.exists(build_command[4])
    assert info.contents == 'FROM continuumio/miniconda3:latest\n\nRUN conda install -c conda-forge -c bioconda transtermhp -p /usr/local --copy --yes \n'


def test_build_stage1_info_singularity():
    repo = 'transtermhp'
    builder = SingularityContainerBuilder(repo=repo, target_args=repo)
    info = builder.build_info(builder.template_stage1)
    build_command = info.build_command
    assert isinstance(build_command, list)
    assert build_command[0] == 'singularity'
    assert build_command[1] == 'build'
    assert build_command[2] == '--fakeroot'
    assert build_command[3].endswith("%s.sif" % repo)
    assert build_command[4].endswith('singularity.def')
    assert os.path.exists(build_command[3])
    assert info.contents == 'Bootstrap: docker\nFrom: continuumio/miniconda3:latest\nStage: build\n%post\n    \n    /opt/conda/bin/conda install -c conda-forge -c bioconda transtermhp -p /usr/local --copy --yes \n    \n%test\n    true\n'


@pytest.mark.parametrize("builder_class", [DockerContainerBuilder, SingularityContainerBuilder])
@pytest.mark.parametrize('repo,target_args,channels,preinstall,postinstall,verbose', [
    ('docker_repo', 'package_a package_b', ['channel_a', 'channel_b'], 'echo "preinstall"', 'echo "postinstall"', False),
    ('docker_repo', 'package_a package_b', ['channel_a', 'channel_b'], 'echo "preinstall"', 'echo "postinstall"', True),
])
def test_build_stage1_variants(builder_class, repo, target_args, channels, preinstall, postinstall, verbose):
    builder = builder_class(repo=repo, target_args=target_args, channels=channels, preinstall=preinstall, postinstall=postinstall, verbose=verbose)
    info = builder.build_info(builder.template_stage1)
    assert info.repo == repo
    assert target_args in info.contents
    for channel in channels:
        assert "-c %s" % channel in info.contents
    assert "%s%s" % (builder.run_prefix, preinstall) in info.contents
    assert "%s%s" % (builder.run_prefix, postinstall) in info.contents
    if verbose:
        assert '--verbose' in info.contents
    else:
        assert '--verbose' not in info.contents


@pytest.mark.parametrize("builder_class", [DockerContainerBuilder, SingularityContainerBuilder])
@external_dependency_management
def test_collect_env_vars(builder_class, artifcat_dir):
    repo = 'transtermhp'
    builder = builder_class(repo=repo, target_args=repo, artifcat_dir=artifcat_dir)
    info = builder.build_info(builder.template_stage1)
    builder.build_stage(info)
    conda_env_vars = builder.get_conda_env_vars()
    assert conda_env_vars == {'TRANSTERMHP': '/usr/local/data/expterm.dat'}


@external_dependency_management
@pytest.mark.parametrize("builder_class", [DockerContainerBuilder, SingularityContainerBuilder])
@pytest.mark.parametrize('image,expect_true', [
    ('transtermhp', False),
    ('multiqc', True)
])
def test_image_requires_extended_base(builder_class, image, expect_true, artifcat_dir):
    builder = builder_class(repo=image, target_args=image, artifcat_dir=artifcat_dir)
    info = builder.build_info(builder.template_stage1)
    builder.build_stage(info)
    assert builder.image_requires_extended_base() == expect_true


@external_dependency_management
@pytest.mark.parametrize("builder_class", [DockerContainerBuilder, SingularityContainerBuilder])
@pytest.mark.parametrize('target_args,destination_image,env_statements', [
    ('transtermhp', DEFAULT_DESTINATION_IMAGE, 'ENV TRANSTERMHP /usr/local/data/expterm.dat'),
    ('multiqc', DEFAULT_EXTENDED_BASE_IMAGE, ''),
])
def test_build_image(builder_class, target_args, destination_image, env_statements, artifcat_dir):
    builder = builder_class(repo=target_args, target_args=target_args, artifcat_dir=artifcat_dir)
    builder.build_image()
    assert "FROM %s" % destination_image in builder.recipe_stage2.contents
    assert env_statements in builder.recipe_stage2.contents
