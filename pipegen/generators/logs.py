from typing import Optional

from pipegen.config import parse_value

from .interfaces import ResourceOutput

LOGICAL_ID = "LogGroup"


def log_group(config) -> Optional[ResourceOutput]:
    """Generate a CodePipeline Pipeline resource"""
    sub_config = config.get("config", {})
    log_group_config = sub_config.get("codebuild", {}).get("log_group", {})

    if not log_group_config.get("enabled") or not log_group_config.get("create"):
        return None

    resource_properties = {
        "KmsKeyId": parse_value("${KmsKeyArn}", KmsKeyArn=sub_config["kms_key_arn"]),
        "LogGroupName": parse_value(
            "${LogGroupName}", LogGroupName=log_group_config.get("name", "AWS::NoValue")
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
