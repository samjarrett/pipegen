import re
from typing import TYPE_CHECKING, Any, Dict, List

from pipegen.config import is_codecommit_with_event_source, parse_value

from .codebuild import generate_logical_id
from .interfaces import ResourceOutput

LOGICAL_ID = "CodePipeline"

ARTIFACT_NAME_PATTERN = re.compile(r"[\W_]+")

if TYPE_CHECKING:  # pragma: no cover
    from typing_extensions import TypedDict

    ActionTypeId = TypedDict(
        "ActionTypeId",
        {"Category": str, "Owner": str, "Provider": str, "Version": int},
    )
    OutputArtifact = TypedDict("OutputArtifact", {"Name": str})
    SourceDefinition = TypedDict(
        "SourceDefinition",
        {
            "Name": str,
            "ActionTypeId": ActionTypeId,
            "Configuration": Dict[str, Any],
            "OutputArtifacts": List[OutputArtifact],
        },
    )
else:
    SourceDefinition = object


def sanitise_artifact_name(name: str) -> str:
    """Sanitise the input/output artifact name"""
    return ARTIFACT_NAME_PATTERN.sub("", name)


def source_action_definition(source: Dict[str, str]) -> SourceDefinition:
    """Get a Source's CodePipeline Action definition"""
    definition: SourceDefinition = {
        "Name": source["name"],
        "ActionTypeId": {
            "Category": "Source",
            "Owner": "AWS",
            "Provider": "CodeCommit",
            "Version": 1,
        },
        "Configuration": {
            "BranchName": parse_value("${BranchName}", BranchName=source["branch"]),
        },
        "OutputArtifacts": [{"Name": sanitise_artifact_name(source["name"])}],
    }

    repository = parse_value("${RepositoryName}", RepositoryName=source["repository"])

    if source["from"] == "CodeCommit":
        definition["Configuration"].update(
            {
                "RepositoryName": repository,
                "PollForSourceChanges": source.get("poll_for_source_changes"),
            }
        )
    if source["from"] == "CodeStarConnection":
        definition["ActionTypeId"].update({"Provider": "CodeStarSourceConnection"})
        definition["Configuration"].update(
            {
                "ConnectionArn": parse_value(
                    "${ConnectionArn}", ConnectionArn=source.get("connection_arn")
                ),
                "FullRepositoryId": repository,
            }
        )

    return definition


def codebuild_action_definition(action, source_names) -> dict:
    """Generate a CodeBuild CodePipeline action definition"""
    primary_source = source_names[0]

    return {
        "Name": action["name"],
        "ActionTypeId": {
            "Category": action["category"],
            "Owner": "AWS",
            "Provider": "CodeBuild",
            "Version": 1,
        },
        "Configuration": {
            "ProjectName": {"Ref": generate_logical_id(action["name"])},
            "PrimarySource": sanitise_artifact_name(primary_source),
        },
        "InputArtifacts": [
            *[{"Name": sanitise_artifact_name(source)} for source in source_names],
            *[
                {"Name": sanitise_artifact_name(input_artifact)}
                for input_artifact in action.get("input_artifacts", [])
            ],
        ],
        "OutputArtifacts": [{"Name": sanitise_artifact_name(action["name"])}],
    }


def pipeline(config, role_logical_id: str) -> ResourceOutput:
    """Generate a CodePipeline Pipeline resource"""
    sub_config = config.get("config", {})

    sources = config.get("sources", [])
    if not sources:
        raise KeyError("At least one source must be supplied")

    source_names = [source["name"] for source in sources]
    if not all(sources):
        raise KeyError("All sources must have a name key + value")

    codebuild_stages = [
        {
            "Name": stage["name"],
            "Actions": [
                codebuild_action_definition(action, source_names)
                for action in stage.get("actions", [])
            ],
        }
        for stage in filter(
            lambda stage: stage.get("enabled"), config.get("stages", [])
        )
    ]

    resource_properties = {
        "ArtifactStore": {
            "EncryptionKey": {
                "Id": parse_value("${KmsKeyArn}", KmsKeyArn=sub_config["kms_key_arn"]),
                "Type": "KMS",
            },
            "Location": parse_value(
                "${BucketName}",
                BucketName=sub_config["s3_bucket"],
            ),
            "Type": "S3",
        },
        "RestartExecutionOnUpdate": sub_config.get("codepipeline", {}).get(
            "restart_execution_on_update"
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


def cloudwatch_events(
    config, cloudwatch_events_role_logical_id: str, codepipeline_logical_id: str
) -> ResourceOutput:
    """Generate a CloudWatch Event to detect source changes"""
    sources = config.get("sources", [])

    source_pattern = re.compile(r"[\W_]+")

    resources = {}

    for source in sources:
        if not is_codecommit_with_event_source(source):
            continue

        # Generate a CFN event
        logical_id = f"{source_pattern.sub('', source['name'])}PushEventRule"

        resources[logical_id] = {
            "Type": "AWS::Events::Rule",
            "Properties": {
                "EventPattern": {
                    "source": ["aws.codecommit"],
                    "detail-type": ["CodeCommit Repository State Change"],
                    "resources": [
                        parse_value(
                            "arn:aws:codecommit:${AWS::Region}:${AWS::AccountId}:${Repository}",
                            Repository=source["repository"],
                        )
                    ],
                    "detail": {
                        "event": ["referenceCreated", "referenceUpdated"],
                        "referenceType": ["branch"],
                        "referenceName": [
                            parse_value("${BranchName}", BranchName=source["branch"])
                        ],
                    },
                },
                "Targets": [
                    {
                        "Arn": {
                            "Fn::Sub": f"arn:aws:codepipeline:${{AWS::Region}}:${{AWS::AccountId}}:${{{codepipeline_logical_id}}}"
                        },
                        "RoleArn": {
                            "Fn::GetAtt": [cloudwatch_events_role_logical_id, "Arn"]
                        },
                        "Id": {"Fn::Sub": f"${{AWS::StackName}}-{logical_id}"},
                    }
                ],
            },
        }

    return ResourceOutput(definition=resources, logical_id="")
