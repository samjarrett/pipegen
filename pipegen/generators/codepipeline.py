from typing import Dict

from pipegen.config import parse_value

from .codebuild import generate_logical_id
from .interfaces import ResourceOutput

LOGICAL_ID = "CodePipeline"


def source_action_definition(source: Dict[str, str]) -> dict:
    """Get a Source's CodePipeline Action definition"""
    if source.get("from", "").lower() == "codecommit":
        return {
            "Name": source.get("name"),
            "ActionTypeId": {
                "Category": "Source",
                "Owner": "AWS",
                "Provider": "CodeCommit",
                "Version": 1,
            },
            "Configuration": {
                "RepositoryName": parse_value(
                    "${RepositoryName}", RepositoryName=source.get("repository")
                ),
                "BranchName": parse_value(
                    "${BranchName}", BranchName=source.get("branch")
                ),
                "PollForSourceChanges": source.get("poll_for_source_changes", False),
            },
            "OutputArtifacts": [{"Name": source.get("name")}],
        }

    raise NotImplementedError(
        f"Source type '{source.get('from', '')}' is not supported yet"
    )


def codebuild_action_definition(action, source_names) -> dict:
    """Generate a CodeBuild CodePipeline action definition"""
    primary_source = source_names[0]

    return {
        "Name": action.get("name"),
        "ActionTypeId": {
            "Category": action.get("category", "Build"),
            "Owner": "AWS",
            "Provider": "CodeBuild",
            "Version": 1,
        },
        "Configuration": {
            "ProjectName": {"Ref": generate_logical_id(action.get("name"))},
            "PrimarySource": primary_source,
        },
        "InputArtifacts": [
            *[{"Name": source} for source in source_names],
            *[
                {"Name": input_artifact}
                for input_artifact in action.get("input_artifacts", [])
            ],
        ],
        "OutputArtifacts": [{"Name": action.get("name")}],
    }


def pipeline(config, role_logical_id: str) -> ResourceOutput:
    """Generate a CodePipeline Pipeline resource"""
    sub_config = config.get("config", {})

    sources = config.get("sources", [])
    if not sources:
        raise KeyError("At least one source must be supplied")

    source_names = [source.get("name") for source in sources]
    if not all(sources):
        raise KeyError("All sources must have a name key + value")

    codebuild_stages = [
        {
            "Name": stage.get("name"),
            "Actions": [
                codebuild_action_definition(action, source_names)
                for action in stage.get("actions", [])
            ],
        }
        for stage in filter(
            lambda stage: stage.get("enabled", True), config.get("stages", [])
        )
    ]

    resource_properties = {
        "ArtifactStore": {
            "EncryptionKey": {
                "Id": parse_value(
                    "${KmsKeyArn}", KmsKeyArn=sub_config.get("kms_key_arn")
                ),
                "Type": "KMS",
            },
            "Location": parse_value(
                "${BucketName}",
                BucketName=sub_config.get("s3_bucket", ""),
            ),
            "Type": "S3",
        },
        "RestartExecutionOnUpdate": sub_config.get("codepipeline", {}).get(
            "restart_execution_on_update", True
        ),
        "RoleArn": {"Fn::GetAtt": [role_logical_id, "Arn"]},
        "Stages": [
            {
                "Name": "Source",
                "Actions": [source_action_definition(source) for source in sources],
            },
            *codebuild_stages,
        ],
    }

    return ResourceOutput(
        definition={
            LOGICAL_ID: {
                "Type": "AWS::CodePipeline::Pipeline",
                "Properties": resource_properties,
            }
        },
        logical_id=LOGICAL_ID,
    )
