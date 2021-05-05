from io import StringIO
from textwrap import dedent
from unittest.mock import patch

from pipegen import cli

MINIMAL_CONFIG = {
    "config": {
        "codepipeline": {"restart_execution_on_update": False},
        "codebuild": {
            "compute_type": "BUILD_GENERAL1_SMALL",
            "image": "aws/codebuild/amazonlinux2-x86_64-standard:3.0",
            "log_group": {"enabled": True, "create": True},
        },
        "iam": [],
        "s3_bucket": "s3-bucket",
        "kms_key_arn": "kms-key-arn",
    },
    "sources": [
        {
            "poll_for_source_changes": False,
            "event_for_source_changes": True,
            "name": "test",
            "from": "CodeStarConnection",
            "repository": "my-test-repo",
            "branch": "main",
            "connection_arn": "connection-arn",
        }
    ],
    "stages": [
        {
            "enabled": True,
            "name": "Build",
            "actions": [
                {
                    "category": "Build",
                    "provider": "CodeBuild",
                    "environment": {},
                    "input_artifacts": [],
                    "name": "Build",
                    "buildspec": "buildspec.yml",
                    "compute_type": "BUILD_GENERAL1_SMALL",
                    "image": "aws/codebuild/amazonlinux2-x86_64-standard:3.0",
                },
                {
                    "category": "Build",
                    "provider": "CodeBuild",
                    "environment": {},
                    "input_artifacts": [],
                    "name": "BuildTwo",
                    "compute_type": "BUILD_GENERAL1_SMALL",
                    "image": "aws/codebuild/amazonlinux2-x86_64-standard:3.0",
                },
            ],
        }
    ],
}


def test_dump_yaml():
    """Tests dump_yaml()"""
    output = StringIO()

    cli.dump_yaml(
        {
            "Hello": ["My Darling", "My Baby", "My Honey"],
            "Key": "Value",
            "Booleans": True,
        },
        output,
    )

    assert output.getvalue() == dedent(
        """\
            Hello:
              - My Darling
              - My Baby
              - My Honey
            Key: Value
            Booleans: true
            """
    )


@patch("pipegen.cli.dump_yaml")
def test_dump_config(patched_dump_yaml):
    """Tests dump_config()"""
    config = StringIO(
        dedent(
            """
            config:
              s3_bucket: s3-bucket
              kms_key_arn: kms-key-arn

            sources:
              - name: test
                from: CodeStarConnection
                repository: my-test-repo
                branch: main
                connection_arn: connection-arn

            stages:
              - name: Build
                actions:
                  - name: Build
                    buildspec: buildspec.yml
                  - name: BuildTwo
            """
        )
    )

    cli.dump_config.callback(config, {})
    patched_dump_yaml.assert_called_once_with(MINIMAL_CONFIG)
