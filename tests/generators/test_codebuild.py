from textwrap import dedent

from pipegen.generators import codebuild


def test_convert_to_yaml():
    """Tests convert_to_yaml()"""

    data = {"hello": True, "thing": {"key": "value"}}
    yaml = dedent(
        """
        hello: true
        thing:
          key: value
        """
    ).strip()
    assert codebuild.convert_to_yaml(data) == yaml


def test_generate_source_config():
    """Tests generate_source_config()"""
    assert codebuild.generate_source_config({"buildspec": "my_buildspec.yml"}) == {
        "Type": "CODEPIPELINE",
        "BuildSpec": "my_buildspec.yml",
    }

    yaml = dedent(
        """
        version: 0.2
        phases:
          build:
            commands:
              - command1
              - command2
              - command3
        """
    ).strip()
    assert codebuild.generate_source_config(
        {"commands": ["command1", "command2", "command3"]}
    ) == {
        "Type": "CODEPIPELINE",
        "BuildSpec": yaml,
    }

    yaml = dedent(
        """
        version: 0.2
        phases:
          build:
            commands:
              - command1
              - command2
              - command3
        artifacts:
          files:
            - file
            - another file
        """
    ).strip()
    assert (
        codebuild.generate_source_config(
            {
                "commands": ["command1", "command2", "command3"],
                "artifacts": ["file", "another file"],
            }
        )
        == {"Type": "CODEPIPELINE", "BuildSpec": yaml}
    )


def test_generate_logical_id():
    """Tests generate_logical_id()"""
    assert codebuild.generate_logical_id("My App") == "CodeBuildMyApp"
    assert codebuild.generate_logical_id("My-App") == "CodeBuildMyApp"
    assert codebuild.generate_logical_id("My_App") == "CodeBuildMyApp"
