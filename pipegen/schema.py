from typing import Dict, List
from typing import Optional as OptionalType
from typing import Set

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

CODEPIPELINE_DEFAULTS: Dict = {
    "restart_execution_on_update": False,
}
CODEBUILD_DEFAULTS: Dict = {
    "compute_type": "BUILD_GENERAL1_SMALL",
    "image": "aws/codebuild/amazonlinux2-x86_64-standard:3.0",
    "log_group": {"enabled": True, "create": True},
}


class UniqueStr(Str):
    """Ensure that a string has a unique value amongst invocations"""

    def __init__(self):
        self.existing_items: Set[str] = set()

    def validate_scalar(self, chunk):
        if chunk.contents in self.existing_items:
            chunk.while_parsing_found("a set of strings", "duplicate found")

        self.existing_items.add(chunk.contents)
        return super().validate_scalar(chunk)


def generate_schema(
    stage_actions: OptionalType[List[str]] = None,
    default_compute_type: OptionalType[str] = None,
    default_image: OptionalType[str] = None,
    log_group_config: OptionalType[Dict] = None,
) -> Map:
    """Generate a schema"""
    input_artifact_validator = Str()
    if stage_actions:
        input_artifact_validator = Enum(stage_actions)

    name_validation_key = Optional("name")
    if (
        log_group_config
        and log_group_config["enabled"]
        and not log_group_config["create"]
    ):
        # name becomes mandatory if we're not creating it and it's enabled
        name_validation_key = "name"

    log_group_validator = {
        Optional(
            "enabled",
            default=CODEBUILD_DEFAULTS["log_group"]["enabled"],
        ): Bool(),
        name_validation_key: Str(),
        Optional(
            "create",
            default=CODEBUILD_DEFAULTS["log_group"]["create"],
        ): Bool(),
        Optional("retention"): Int(),
    }

    return Map(
        {
            "config": Map(
                {
                    "s3_bucket": Str(),
                    "kms_key_arn": Str(),
                    Optional("codepipeline", default=CODEPIPELINE_DEFAULTS,): Map(
                        {
                            Optional(
                                "restart_execution_on_update",
                                default=CODEPIPELINE_DEFAULTS[
                                    "restart_execution_on_update"
                                ],
                            ): Bool(),
                        }
                    ),
                    Optional("codebuild", default=CODEBUILD_DEFAULTS): Map(
                        {
                            Optional(
                                "compute_type",
                                default=CODEBUILD_DEFAULTS["compute_type"],
                            ): Str(),
                            Optional(
                                "image",
                                default=CODEBUILD_DEFAULTS["image"],
                            ): Str(),
                            Optional(
                                "log_group",
                                default=CODEBUILD_DEFAULTS["log_group"],
                            ): Map(log_group_validator),
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
                        "name": UniqueStr(),
                        "from": Enum(["CodeCommit", "CodeStarConnection"]),
                        "repository": Str(),
                        "branch": Str(),
                        Optional("poll_for_source_changes", default=False): Bool(),
                        Optional("event_for_source_changes", default=True): Bool(),
                        Optional("connection_arn"): Str(),
                    }
                )
            ),
            "stages": Seq(
                Map(
                    {
                        "name": UniqueStr(),
                        Optional("enabled", default=True): Bool(),
                        "actions": Seq(
                            Map(
                                {
                                    "name": UniqueStr(),
                                    Optional("category", default="Build"): Enum(
                                        ["Build", "Test", "Deploy"]
                                    ),
                                    Optional("provider", default="CodeBuild"): Enum(
                                        ["CodeBuild"]
                                    ),
                                    Optional("buildspec"): Str(),
                                    Optional("commands"): Seq(Str()),
                                    Optional("artifacts"): Seq(Str()),
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
