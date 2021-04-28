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
    }

    name = log_group_config.get("name")
    if name:
        resource_properties["LogGroupName"] = parse_value(
            "${LogGroupName}", LogGroupName=name
        )
    retention = log_group_config.get("retention")
    if retention:
        resource_properties["RetentionInDays"] = parse_value(
            "${Retention}", Retention=retention
        )

    return ResourceOutput(
        definition={
            LOGICAL_ID: {
                "Type": "AWS::Logs::LogGroup",
                "Properties": resource_properties,
            }
        },
        logical_id=LOGICAL_ID,
    )
