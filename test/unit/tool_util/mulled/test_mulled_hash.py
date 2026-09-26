from galaxy.tool_util.deps.mulled.mulled_hash import main


def test_conda_hash_cli(capsys):
    main(["--hash", "conda", "bedtools=2.30.0,samtools=1.9"])

    assert (
        capsys.readouterr().out.strip() == "mulled-v1-ca195b12c14e35565e393a2d07f2deac7610d8126cc3460d217504efd11d4347"
    )
