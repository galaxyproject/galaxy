import os

import pytest

from galaxy.tool_util.deps.mulled.docker_build import (
    DEFAULT_DESTINATION_IMAGE,
    DEFAULT_EXTENDED_BASE_IMAGE,
    DockerContainerBuilder,
)


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


@pytest.mark.parametrize('repo,target_args,channels,preinstall,postinstall,verbose', [
    ('docker_repo', 'package_a package_b', ['channel_a', 'channel_b'], 'echo "preinstall"', 'echo "postinstall"', False),
    ('docker_repo', 'package_a package_b', ['channel_a', 'channel_b'], 'echo "preinstall"', 'echo "postinstall"', True),
])
def test_build_stage1_variants(repo, target_args, channels, preinstall, postinstall, verbose):
    builder = DockerContainerBuilder(repo=repo, target_args=target_args, channels=channels, preinstall=preinstall, postinstall=postinstall, verbose=verbose)
    info = builder.build_info(builder.template_stage1)
    assert info.repo == repo
    assert target_args in info.contents
    for channel in channels:
        assert "-c %s" % channel in info.contents
    assert "RUN %s" % preinstall in info.contents
    assert "RUN %s" % postinstall in info.contents
    if verbose:
        assert '--verbose' in info.contents
    else:
        assert '--verbose' not in info.contents


def test_collect_env_vars():
    repo = 'transtermhp'
    builder = DockerContainerBuilder(repo=repo, target_args=repo)
    info = builder.build_info(builder.template_stage1)
    builder.build_stage(info)
    conda_env_vars = builder.get_conda_env_vars()
    assert conda_env_vars == {'TRANSTERMHP': '/usr/local/data/expterm.dat'}


@pytest.mark.parametrize('image,expect_true', [
    ('transtermhp', False),
    ('multiqc', True)
])
def test_image_requires_extended_base(image, expect_true):
    builder = DockerContainerBuilder(repo=image, target_args=image)
    info = builder.build_info(builder.template_stage1)
    builder.build_stage(info)
    assert builder.image_requires_extended_base() == expect_true


@pytest.mark.parametrize('target_args,destination_image,env_statements', [
    ('transtermhp', DEFAULT_DESTINATION_IMAGE, 'ENV TRANSTERMHP /usr/local/data/expterm.dat'),
    ('multiqc', DEFAULT_EXTENDED_BASE_IMAGE, ''),
])
def test_build_image(target_args, destination_image, env_statements):
    builder = DockerContainerBuilder(repo=target_args, target_args=target_args)
    builder.build_image()
    assert "FROM %s" % destination_image in builder.recipe_stage2.contents
    assert env_statements in builder.recipe_stage2.contents
