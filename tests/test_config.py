import pytest

from pipegen import config

REPO_URI_PREFIX = "123456789012.dkr.ecr.my-region-1.amazonaws.com"


def test_parse_config():
    """Tests parse_config()"""
    check_config = """
    key: value
    hello: stuff
    """
    assert config.parse_config(check_config, {}) == {"key": "value", "hello": "stuff"}

    check_config = """
    key: value
    hello: {{ vars.my_var }}
    """
    assert config.parse_config(check_config, {"my_var": "my_value"}) == {
        "key": "value",
        "hello": "my_value",
    }

    check_config = """
    key: value
    hello: {{ vars.my_var | default("my default value") }}
    """
    assert config.parse_config(check_config, {}) == {
        "key": "value",
        "hello": "my default value",
    }


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
