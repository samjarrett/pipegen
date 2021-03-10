import re
from functools import reduce
from typing import Any, NamedTuple

from pipegen.config import parse_value

PROJECT_LOGICAL_ID_PATTERN = re.compile(r"[\W_]+")


class CodeBuildProjectResourceOutput(NamedTuple):
    """An IAM Resource's output"""

    definition: dict[str, Any]
    logical_id: str


def generate_logical_id(name: str) -> str:
    """Generate CodeBuild logical resource ID"""
    return f"CodeBuild{PROJECT_LOGICAL_ID_PATTERN.sub('', name)}"


def get_codebuild_projects(config):
    """Get all the codebuild projects required"""
    sub_config = config.get("config", {})
    default_image = sub_config.get("codebuild", {}).get("image")
    default_compute_type = sub_config.get("codebuild", {}).get("compute_type")

    def project_reducer(existing, stage: dict):
        """The reducer"""
        if stage.get("enabled", True):
            existing.extend(stage["actions"])
        return existing

    def project_default_values(project: dict):
        """Insert the default values"""
        project.setdefault("image", default_image)
        project.setdefault("compute_type", default_compute_type)
        return project

    projects = list(
        map(project_default_values, reduce(project_reducer, config["stages"], []))
    )

    return projects


def codebuild_project(
    project_config, sub_config: dict, role_logical_id: str
) -> CodeBuildProjectResourceOutput:
    """Generate a CodeBuild project resource"""
    logical_id = generate_logical_id(project_config["name"])

    environment_variables = project_config.get("environment", {})
    environment_variables.setdefault("AWS_DEFAULT_REGION", "AWS::Region")
    environment_variables.setdefault("AWS_REGION", "AWS::Region")

    resource_properties = {
        "Artifacts": {"Type": "CODEPIPELINE"},
        "Environment": {
            "ComputeType": parse_value(
                "${ComputeType}", ComputeType=project_config["compute_type"]
            ),
            "Image": parse_value("${Image}", Image=project_config["image"]),
            "ImagePullCredentialsType": "SERVICE_ROLE",
            "EnvironmentVariables": [
                {"Name": key, "Value": parse_value("${Value}", Value=value)}
                for key, value in environment_variables.items()
            ],
            "PrivilegedMode": False,
            "Type": "LINUX_CONTAINER",
        },
        "ServiceRole": {"Fn::GetAtt": [role_logical_id, "Arn"]},
        "Source": {
            "BuildSpec": parse_value(
                "${BuildSpec}", BuildSpec=project_config["buildspec"]
            ),
            "Type": "CODEPIPELINE",
        },
        "EncryptionKey": parse_value(
            "${KmsKeyArn}", KmsKeyArn=sub_config.get("kms_key_arn")
        ),
    }

    log_group = sub_config.get("codebuild", {}).get("log_group", {})
    if log_group.get("enabled", False):
        resource_properties.update(
            {
                "LogsConfig": {
                    "CloudWatchLogs": {
                        "GroupName": parse_value(
                            "${GroupName}", GroupName=log_group.get("name")
                        ),
                        "Status": "ENABLED",
                    }
                }
            }
        )

    return CodeBuildProjectResourceOutput(
        definition={
            logical_id: {
                "Type": "AWS::CodeBuild::Project",
                "Properties": resource_properties,
            }
        },
        logical_id=logical_id,
    )
