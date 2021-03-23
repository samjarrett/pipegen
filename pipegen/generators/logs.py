from typing import Optional

from pipegen.config import parse_value

from .interfaces import ResourceOutput

LOGICAL_ID = "LogGroup"


def log_group(config) -> Optional[ResourceOutput]:
    """Generate a CodePipeline Pipeline resource"""
    sub_config = config.get("config", {})
    log_group_config = sub_config.get("codebuild", {}).get("log_group", {})

    if not log_group_config.get("enabled", False) or not log_group_config.get(
        "create", True
    ):
        return None

    resource_properties = {
        "KmsKeyId": parse_value(
            "${KmsKeyArn}", KmsKeyArn=sub_config.get("kms_key_arn", "AWS::NoValue")
        ),
        "LogGroupName": parse_value(
            "${LogGroupName}", LogGroupName=log_group_config.get("name")
        ),
        "RetentionInDays": parse_value(
            "${Retention}", Retention=log_group_config.get("retention", "AWS::NoValue")
        ),
    }

    return ResourceOutput(
        definition={
            LOGICAL_ID: {
                "Type": "AWS::Logs::LogGroup",
                "Properties": resource_properties,
            }
        },
        logical_id=LOGICAL_ID,
    )
