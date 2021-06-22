import re
from functools import reduce
from io import StringIO
from typing import Any, Dict, Optional

from strictyaml.ruamel import YAML

from pipegen.config import get_ecr_arn, parse_value

from .interfaces import ResourceOutput

PROJECT_LOGICAL_ID_PATTERN = re.compile(r"[\W_]+")


def convert_to_yaml(template) -> str:
    """Convert a python variable to YAML"""
    output = StringIO()
    yaml = YAML()
    yaml.indent(sequence=4, offset=2)
    yaml.dump(template, output)
    return output.getvalue()


def generate_source_config(project_config) -> Dict[str, Any]:
    """Generate a source config entry for a project config"""

    source: Dict[str, Any] = {"Type": "CODEPIPELINE"}

    if project_config.get("buildspec"):
        source["BuildSpec"] = parse_value(
            "${BuildSpec}", BuildSpec=project_config["buildspec"]
        )
    elif project_config.get("commands"):
        template = {
            "version": 0.2,
            "phases": {"build": {"commands": project_config["commands"]}},
        }

        artifacts = project_config.get("artifacts")
        if artifacts:
            template.update({"artifacts": {"files": artifacts}})

        source["BuildSpec"] = convert_to_yaml(template)

    return source


def generate_logical_id(name: str) -> str:
    """Generate CodeBuild logical resource ID"""
    return f"CodeBuild{PROJECT_LOGICAL_ID_PATTERN.sub('', name)}"


def get_codebuild_projects(config):
    """Get all the codebuild projects required"""

    def project_reducer(existing, stage: dict):
        """The reducer"""
        if stage.get("enabled"):
            existing.extend(stage["actions"])
        return existing

    projects = list(reduce(project_reducer, config["stages"], []))

    return projects


def is_ecr(image: str) -> bool:
    """Determines if the image is from ECR or not"""
    try:
        get_ecr_arn(image)
        return True
    except RuntimeError:
        return False


def project(
    project_config,
    sub_config: dict,
    role_logical_id: str,
    log_group_logical_id: Optional[str] = None,
) -> ResourceOutput:
    """Generate a CodeBuild project resource"""
    logical_id = generate_logical_id(project_config["name"])

    environment_variables = project_config.get("environment", {})
    environment_variables.setdefault("AWS_DEFAULT_REGION", "AWS::Region")
    environment_variables.setdefault("AWS_REGION", "AWS::Region")

    image_credential_type = (
        "SERVICE_ROLE" if is_ecr(project_config["image"]) else "CODEBUILD"
    )

    resource_properties = {
        "Artifacts": {"Type": "CODEPIPELINE"},
        "Environment": {
            "ComputeType": parse_value(
                "${ComputeType}", ComputeType=project_config["compute_type"]
            ),
            "Image": parse_value("${Image}", Image=project_config["image"]),
            "ImagePullCredentialsType": image_credential_type,
            "EnvironmentVariables": [
                {"Name": key, "Value": parse_value("${Value}", Value=value)}
                for key, value in environment_variables.items()
            ],
            "PrivilegedMode": False,
            "Type": "LINUX_CONTAINER",
        },
        "ServiceRole": {"Fn::GetAtt": [role_logical_id, "Arn"]},
        "Source": generate_source_config(project_config),
        "EncryptionKey": parse_value(
            "${KmsKeyArn}", KmsKeyArn=sub_config["kms_key_arn"]
        ),
    }

    log_group = sub_config.get("codebuild", {}).get("log_group", {})
    if log_group.get("enabled"):
        log_group_name = parse_value("${GroupName}", GroupName=log_group.get("name"))
        if log_group_logical_id:
            log_group_name = {"Ref": log_group_logical_id}

        resource_properties.update(
            {
                "LogsConfig": {
                    "CloudWatchLogs": {
                        "GroupName": log_group_name,
                        "Status": "ENABLED",
                    }
                }
            }
        )
    else:
        resource_properties.update(
            {
                "LogsConfig": {
                    "CloudWatchLogs": {
                        "Status": "DISABLED",
                    }
                }
            }
        )

    return ResourceOutput(
        definition={
            logical_id: {
                "Type": "AWS::CodeBuild::Project",
                "Properties": resource_properties,
            }
        },
        logical_id=logical_id,
    )
