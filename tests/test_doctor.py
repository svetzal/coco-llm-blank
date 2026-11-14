import doctor


def test_doctor_finds_executables_and_explicit_paths(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("PATH", str(tmp_path))
    for command, (variable, _) in doctor.TOOLS.items():
        monkeypatch.delenv(variable, raising=False)
        executable = tmp_path / command
        executable.write_text("#!/bin/sh\nexit 99\n")
        executable.chmod(0o755)
    assert doctor.main([]) == 0
    assert str(tmp_path / "lwasm") in capsys.readouterr().out
    (tmp_path / "decb").unlink()
    assert doctor.main([]) == 1
    assert "decb: missing" in capsys.readouterr().out
    alternate = tmp_path / "alternate-decb"
    alternate.write_text("#!/bin/sh\nexit 99\n")
    alternate.chmod(0o755)
    monkeypatch.setenv("DECB", str(alternate))
    assert doctor.main([]) == 0
    alternate.chmod(0o644)
    assert doctor.main([]) == 1
