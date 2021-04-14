from typing import Optional

from pipegen.generators import logs


def configure_log_group(
    enabled: bool, create: bool, name: str, retention: Optional[int] = None
):
    """Generate a config entry for a log group"""
    log_config = {
        "enabled": enabled,
        "create": create,
        "name": name,
    }
    if retention:
        log_config["retention"] = retention

    return {
        "config": {
            "kms_key_arn": "kms-key-arn",
            "codebuild": {"log_group": log_config},
        }
    }


def test_log_group_disabled():
    """Tests log_group() when it is disabled"""
    assert logs.log_group(configure_log_group(False, True, "my-log-group")) is None


def test_log_group_no_create():
    """Tests log_group() when creating the group is disabled"""
    assert logs.log_group(configure_log_group(True, False, "my-log-group")) is None


def test_log_group_basic_config():
    """Tests log_group() when creating the group with basic config"""
    resource_config = logs.log_group(configure_log_group(True, True, "my-log-group"))
    assert resource_config.logical_id == "LogGroup"
    assert resource_config.definition == {
        "LogGroup": {
            "Type": "AWS::Logs::LogGroup",
            "Properties": {
                "KmsKeyId": "kms-key-arn",
                "LogGroupName": "my-log-group",
                "RetentionInDays": {"Ref": "AWS::NoValue"},
            },
        }
    }

    resource_config = logs.log_group(configure_log_group(True, True, "my-log-group", 7))
    assert resource_config.definition == {
        "LogGroup": {
            "Type": "AWS::Logs::LogGroup",
            "Properties": {
                "KmsKeyId": "kms-key-arn",
                "LogGroupName": "my-log-group",
                "RetentionInDays": 7,
            },
        }
    }
