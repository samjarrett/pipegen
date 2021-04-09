from typing import List
from typing import Optional as OptionalType

from strictyaml import (
    Bool,
    EmptyDict,
    EmptyList,
    Enum,
    Int,
    Map,
    MapPattern,
    Optional,
    Seq,
    Str,
)


def generate_schema(
    stage_actions: OptionalType[List[str]] = None,
    default_compute_type: OptionalType[str] = None,
    default_image: OptionalType[str] = None,
) -> Map:
    """Generate a schema"""
    input_artifact_validator = Str()
    if stage_actions:
        input_artifact_validator = Enum(stage_actions)

    return Map(
        {
            "config": Map(
                {
                    "s3_bucket": Str(),
                    "kms_key_arn": Str(),
                    Optional(
                        "codepipeline", default={"restart_execution_on_update": False}
                    ): Map(
                        {
                            Optional(
                                "restart_execution_on_update", default=False
                            ): Bool(),
                        }
                    ),
                    "codebuild": Map(
                        {
                            Optional(
                                "compute_type", default="BUILD_GENERAL1_SMALL"
                            ): Str(),
                            Optional(
                                "image",
                                default="aws/codebuild/amazonlinux2-x86_64-standard:3.0",
                            ): Str(),
                            "log_group": Map(
                                {
                                    Optional("enabled", default=False): Bool(),
                                    Optional("name"): Str(),
                                    Optional("create", default=True): Bool(),
                                    Optional("retention"): Int(),
                                }
                            ),
                        }
                    ),
                    Optional("iam", default=[]): EmptyList()
                    | Seq(
                        Map(
                            {
                                Optional("Effect", default="Allow"): Enum(
                                    ["Allow", "Deny"]
                                ),
                                "Action": Seq(Str()),
                                "Resource": Seq(Str()),
                            }
                        )
                    ),
                }
            ),
            "sources": Seq(
                Map(
                    {
                        "name": Str(),
                        "from": Enum(["CodeCommit"]),
                        "repository": Str(),
                        "branch": Str(),
                        Optional("poll_for_source_changes", default=False): Bool(),
                    }
                )
            ),
            "stages": Seq(
                Map(
                    {
                        "name": Str(),
                        Optional("enabled", default=True): Bool(),
                        "actions": Seq(
                            Map(
                                {
                                    "name": Str(),
                                    Optional("category", default="Build"): Enum(
                                        ["Build", "Test", "Deploy"]
                                    ),
                                    Optional("provider", default="CodeBuild"): Enum(
                                        ["CodeBuild"]
                                    ),
                                    "buildspec": Str(),
                                    Optional(
                                        "compute_type",
                                        default=default_compute_type,
                                    ): Str(),
                                    Optional("image", default=default_image): Str(),
                                    Optional("environment", default={}): EmptyDict()
                                    | MapPattern(Str(), Str()),
                                    Optional("input_artifacts", default=[]): EmptyList()
                                    | Seq(input_artifact_validator),
                                }
                            )
                        ),
                    }
                )
            ),
        }
    )
