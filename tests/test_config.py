from unittest.mock import patch

import pytest
from strictyaml import Any
from strictyaml.exceptions import YAMLValidationError

from pipegen import config

REPO_URI_PREFIX = "123456789012.dkr.ecr.my-region-1.amazonaws.com"


@patch("pipegen.config.generate_schema", return_value=Any())
def test_load_config(patched_generate_schema):
    """Tests load_config()"""
    check_config = """
    key: value
    hello: stuff
    """
    assert config.load_config(check_config, {}) == {"key": "value", "hello": "stuff"}
    patched_generate_schema.assert_called_once()

    check_config = """
    key: value
    hello: {{ vars.my_var }}
    """
    assert config.load_config(check_config, {"my_var": "my_value"}) == {
        "key": "value",
        "hello": "my_value",
    }

    check_config = """
    key: value
    hello: {{ vars.my_var | default("my default value") }}
    """
    assert config.load_config(check_config, {}) == {
        "key": "value",
        "hello": "my default value",
    }


def test_parse_config():
    """Tests parse_config()"""
    check_config = """
    config:
        s3_bucket: my-bucket
        kms_key_arn: kms-key-arn

    sources:
        - name: Source
          from: CodeCommit
          repository: my-repo
          branch: main

    stages:
        - name: Build
          actions:
            - name: Build
              provider: CodeBuild
              buildspec: buildspecs/build.yml
    """
    rendered_config = config.parse_config(check_config, {})
    assert rendered_config is not None

    # Test that base defaults are applied
    assert rendered_config["config"]["codebuild"] is not None
    assert (
        rendered_config["config"]["codebuild"]["compute_type"] == "BUILD_GENERAL1_SMALL"
    )
    assert (
        rendered_config["config"]["codebuild"]["image"]
        == "aws/codebuild/amazonlinux2-x86_64-standard:3.0"
    )
    assert rendered_config["config"]["codebuild"]["log_group"] == {
        "enabled": False,
        "create": True,
    }

    # Test compute_type and image defaults pass through to build stages
    check_config = """
    config:
        s3_bucket: my-bucket
        kms_key_arn: kms-key-arn

        codebuild:
            compute_type: BUILD_GENERAL1_SMALL
            image: codebuild-image
        
            log_group: 
                enabled: false

    sources:
        - name: Source
          from: CodeCommit
          repository: my-repo
          branch: main

    stages:
        - name: Build
          actions:
            - name: Build
              provider: CodeBuild
              buildspec: buildspecs/build.yml
    """
    rendered_config = config.parse_config(check_config, {})
    for stage in rendered_config["stages"]:
        for action in stage["actions"]:
            assert action["compute_type"] == "BUILD_GENERAL1_SMALL"
            assert action["image"] == "codebuild-image"

    # Test that input_artifacts are validated correctly - this should exception
    check_config = """
    config:
        s3_bucket: my-bucket
        kms_key_arn: kms-key-arn

        codebuild:
            compute_type: BUILD_GENERAL1_SMALL
            image: codebuild-image
        
            log_group: 
                enabled: false

    sources:
        - name: Source
          from: CodeCommit
          repository: my-repo
          branch: main

    stages:
        - name: Build
          actions:
            - name: Build
              provider: CodeBuild
              buildspec: buildspecs/build.yml
              input_artifacts:
                - SomeOtherStage
    """
    with pytest.raises(YAMLValidationError):
        config.parse_config(check_config, {})


def test_parse_value_single_value():
    """Tests parse_value() when passed a single value"""
    assert config.parse_value("${Value}", Value="my-value") == "my-value"

    assert config.parse_value("${Value}", Value="AWS::NoValue") == {
        "Ref": "AWS::NoValue"
    }


def test_parse_value_import():
    """Tests parse_value() when passed an import"""
    assert config.parse_value("${Value}", Value="import:MyImport") == {
        "Fn::Sub": ("${Value}", {"Value": {"Fn::ImportValue": "MyImport"}})
    }

    assert config.parse_value("Prefix-${Value}-Suffix", Value="import:MyImport") == {
        "Fn::Sub": (
            "Prefix-${Value}-Suffix",
            {"Value": {"Fn::ImportValue": "MyImport"}},
        )
    }


def test_get_ecr_arn():
    """Tests get_ecr_arn()"""
    assert (
        config.get_ecr_arn(f"{REPO_URI_PREFIX}/repo")
        == "arn:aws:ecr:my-region-1:123456789012:repository/repo"
    )
    assert (
        config.get_ecr_arn(f"{REPO_URI_PREFIX}/repo/path")
        == "arn:aws:ecr:my-region-1:123456789012:repository/repo/path"
    )
    assert (
        config.get_ecr_arn(f"{REPO_URI_PREFIX}/repo/path:tag")
        == "arn:aws:ecr:my-region-1:123456789012:repository/repo/path"
    )


def test_get_ecr_arn_exception():
    """Tests get_ecr_arn() when it raises an exception"""
    with pytest.raises(RuntimeError) as excinfo:
        config.get_ecr_arn("something not like an ecr uri")

    assert "URI provided doesn't appear to be an ECR URI" in str(excinfo.value)
