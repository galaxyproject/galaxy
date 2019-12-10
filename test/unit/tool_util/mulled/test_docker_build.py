import os

import pytest

from galaxy.tool_util.deps.mulled.docker_build import (
    build_image,
    build_initial_docker_info,
    collect_conda_env_vars,
    get_destination_docker_info,
    DEFAULT_DESTINATION_IMAGE,
    DEFAULT_EXTENDED_BASE_IMAGE,
    image_requires_extended_base,
)


def test_build_initial_docker_info():
    repo = 'transtermhp'
    docker_info = build_initial_docker_info(repo=repo, target_args=repo)
    build_command = docker_info.build_command
    assert isinstance(build_command, list)
    assert build_command[0] == 'docker'
    assert build_command[1] == 'build'
    assert build_command[2] == '-t'
    assert build_command[3] == repo
    assert os.path.exists(build_command[4])
    assert docker_info.contents == 'FROM continuumio/miniconda3:latest\n\nRUN conda install -c conda-forge -c bioconda transtermhp -p /usr/local --copy --yes \n'


@pytest.mark.parametrize('repo,target_args,channels,preinstall,postinstall,verbose', [
    ('docker_repo', 'package_a package_b', ['channel_a', 'channel_b'], 'echo "preinstall"', 'echo "postinstall"', False),
    ('docker_repo', 'package_a package_b', ['channel_a', 'channel_b'], 'echo "preinstall"', 'echo "postinstall"', True),
])
def test_build_initial_docker_info_variants(repo, target_args, channels, preinstall, postinstall, verbose):
    docker_info = build_initial_docker_info(
        repo=repo,
        target_args=target_args,
        channels=channels,
        preinstall=preinstall,
        postinstall=postinstall,
        verbose=verbose,
    )
    assert docker_info.repo == repo
    assert target_args in docker_info.contents
    for channel in channels:
        assert "-c %s" % channel in docker_info.contents
    assert "RUN %s" % preinstall in docker_info.contents
    assert "RUN %s" % postinstall in docker_info.contents
    if verbose:
        assert '--verbose' in docker_info.contents
    else:
        assert '--verbose' not in docker_info.contents


def test_collect_env_vars():
    repo = 'transtermhp'
    docker_info = build_initial_docker_info(repo=repo, target_args='transtermhp')
    build_image(docker_info)
    conda_env_vars = collect_conda_env_vars(image=repo)
    assert conda_env_vars == {'TRANSTERMHP': '/usr/local/data/expterm.dat'}


@pytest.mark.parametrize('image,expect_true', [
    ('transtermhp', False),
    ('multiqc', True)
])
def test_image_requires_extended_base(image, expect_true):
    docker_info = build_initial_docker_info(repo=image, target_args=image)
    build_image(docker_info)
    assert image_requires_extended_base(image=image) == expect_true


@pytest.mark.parametrize('target_args,destination_image,env_statements', [
    ('transtermhp', DEFAULT_DESTINATION_IMAGE, 'ENV TRANSTERMHP /usr/local/data/expterm.dat'),
    ('multiqc', DEFAULT_EXTENDED_BASE_IMAGE, ''),
])
def test_get_destination_docker_info(target_args, destination_image, env_statements):
    initial_docker_info = build_initial_docker_info(repo=target_args, target_args=target_args)
    build_image(initial_docker_info)
    destination_docker_info = get_destination_docker_info(initial_docker_info)
    assert "FROM %s" % destination_image in destination_docker_info.contents
    assert env_statements in destination_docker_info.contents
