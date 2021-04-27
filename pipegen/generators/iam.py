from copy import copy
from typing import TYPE_CHECKING, Iterable, List, Optional, Set, Union

from pipegen.config import FnGetAtt, FnSub, Ref, get_ecr_arn, parse_value

from .interfaces import ResourceOutput

if TYPE_CHECKING:  # pragma: no cover
    from typing_extensions import TypedDict
else:
    TypedDict = object

S3_BUCKET_PERMISSIONS = [
    "s3:GetObject*",
    "s3:GetBucket*",
    "s3:List*",
    "s3:DeleteObject*",
    "s3:PutObject*",
    "s3:Abort*",
]
KMS_KEY_PERMISSIONS = [
    "kms:Decrypt",
    "kms:DescribeKey",
    "kms:Encrypt",
    "kms:GenerateDataKey*",
    "kms:ReEncrypt*",
]
CODEPIPELINE_CODEBUILD_PERMISSIONS = [
    "codebuild:BatchGetBuilds",
    "codebuild:StartBuild",
    "codebuild:StopBuild",
]


class IAMPermissionDict(TypedDict):
    """An IAM Permission Dictionary"""

    Effect: str
    Action: List[str]
    Resource: List[Union[str, FnSub, FnGetAtt, Ref]]


def iam_permission(
    action: List[str], resource: List[Union[str, FnSub, FnGetAtt, Ref]]
) -> IAMPermissionDict:
    """Return an IAM permission"""
    return {
        "Effect": "Allow",
        "Action": action,
        "Resource": resource,
    }


def get_ecr_arns(image_list: List[Optional[str]]) -> Iterable[str]:
    """Reduce a list of images to ECR ARNs"""
    for image in image_list:
        try:
            arn = get_ecr_arn(str(image))
            yield arn
        except RuntimeError:
            pass


def generate_managed_policy(resource_name: str, permissions):
    """Generate an IAM Managed Policy resource"""
    return {
        resource_name: {
            "Type": "AWS::IAM::ManagedPolicy",
            "Properties": {
                "PolicyDocument": {"Version": "2012-10-17", "Statement": permissions}
            },
        }
    }


def generate_role(resource_name: str, service: str, managed_policies: List[str]):
    """Generate an IAM Role resource"""
    return {
        resource_name: {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": service},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                },
                "ManagedPolicyArns": [{"Ref": policy} for policy in managed_policies],
            },
        }
    }


def codepipeline_role(config, codebuild_projects: List[str]) -> ResourceOutput:
    """Generate a CodePipeline role + policy resources"""
    sub_config = config.get("config", {})
    permissions = [
        iam_permission(
            copy(S3_BUCKET_PERMISSIONS),
            [
                parse_value(
                    "arn:aws:s3:::${BucketName}",
                    BucketName=str(sub_config["s3_bucket"]),
                ),
                parse_value(
                    "arn:aws:s3:::${BucketName}/*",
                    BucketName=str(sub_config["s3_bucket"]),
                ),
            ],
        ),
        iam_permission(
            copy(KMS_KEY_PERMISSIONS),
            [
                parse_value(
                    "${KmsKeyArn}",
                    KmsKeyArn=sub_config["kms_key_arn"],
                )
            ],
        ),
        iam_permission(
            copy(CODEPIPELINE_CODEBUILD_PERMISSIONS),
            [
                {"Fn::GetAtt": [codebuild_project, "Arn"]}
                for codebuild_project in codebuild_projects
            ],
        ),
    ]

    # Add Source perms
    codecommit_projects: List[Union[str, FnSub, FnGetAtt, Ref]] = []
    codestar_connection_arns: Set[str] = set()
    for source in config.get("sources", []):
        if source["from"] == "CodeCommit":
            codecommit_projects.append(
                parse_value(
                    "arn:aws:codecommit:${AWS::Region}:${AWS::AccountId}:${RepositoryName}",
                    RepositoryName=source["repository"],
                )
            )
        elif source["from"] == "CodeStarConnection":
            if not source.get("connection_arn"):
                raise RuntimeError(
                    f"Source {source['name']} uses CodeStar Connections, but does not specify a connection_arn"
                )
            codestar_connection_arns.add(source.get("connection_arn"))
        else:
            raise NotImplementedError(
                f"Source type '{source['from']}' is not supported yet"
            )

    if codecommit_projects:
        permissions.append(
            iam_permission(
                [
                    "codecommit:GetBranch",
                    "codecommit:GetCommit",
                    "codecommit:GetUploadArchiveStatus",
                    "codecommit:UploadArchive",
                    "codecommit:GitPull",
                ],
                codecommit_projects,
            )
        )
    if codestar_connection_arns:
        permissions.append(
            iam_permission(
                [
                    "codestar-connections:UseConnection",
                ],
                [
                    parse_value(
                        "${ConnectionArn}",
                        ConnectionArn=connection_arn,
                    )
                    for connection_arn in sorted(codestar_connection_arns)
                ],
            )
        )

    return ResourceOutput(
        definition={
            **generate_role(
                "CodePipelineRole", "codepipeline.amazonaws.com", ["CodePipelinePolicy"]
            ),
            **generate_managed_policy("CodePipelinePolicy", permissions),
        },
        logical_id="CodePipelineRole",
    )


def codebuild_role(
    config, log_group_logical_id: Optional[str] = None
) -> ResourceOutput:
    """Generate a CodeBuild role + policy resources"""
    sub_config = config.get("config", {})
    permissions = []

    # Add CW Logs perms
    log_group = sub_config.get("codebuild", {}).get("log_group", {})
    if log_group.get("enabled"):
        log_group_arn: Union[str, FnSub, Ref, FnGetAtt] = parse_value(
            "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:${LogGroupName}:*",
            LogGroupName=log_group.get("name"),
        )
        if log_group_logical_id:
            log_group_arn = {"Fn::GetAtt": [log_group_logical_id, "Arn"]}

        permissions.append(
            iam_permission(
                ["logs:CreateLogStream", "logs:PutLogEvents"],
                [log_group_arn],
            )
        )

    images = set()
    for stage in config.get("stages", []):
        for action in stage.get("actions", []):
            images.add(action["image"])

    image_arns = sorted(list(get_ecr_arns(list(images))))
    if image_arns:
        permissions.extend(
            [
                iam_permission(["ecr:GetAuthorizationToken"], ["*"]),
                iam_permission(
                    ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"], image_arns  # type: ignore
                ),
            ]
        )

    # Add S3 and KMS perms
    permissions.extend(
        [
            iam_permission(
                copy(S3_BUCKET_PERMISSIONS),
                [
                    parse_value(
                        "arn:aws:s3:::${BucketName}",
                        BucketName=sub_config["s3_bucket"],
                    ),
                    parse_value(
                        "arn:aws:s3:::${BucketName}/*",
                        BucketName=sub_config["s3_bucket"],
                    ),
                ],
            ),
            iam_permission(
                copy(KMS_KEY_PERMISSIONS),
                [
                    parse_value(
                        "${KmsKeyArn}",
                        KmsKeyArn=sub_config["kms_key_arn"],
                    )
                ],
            ),
        ]
    )

    # Add any additionally specified IAM perms
    iam = sub_config.get("iam")
    if iam:
        permissions.extend(iam)

    return ResourceOutput(
        definition={
            **generate_role(
                "CodeBuildRole", "codebuild.amazonaws.com", ["CodeBuildPolicy"]
            ),
            **generate_managed_policy("CodeBuildPolicy", permissions),
        },
        logical_id="CodeBuildRole",
    )


def cloud_watch_event_role(codepipeline_logical_id: str) -> ResourceOutput:
    """Generate a CloudWatch event role to kick off CodePipelines"""
    permissions = [
        iam_permission(
            ["codepipeline:StartPipelineExecution"],
            [
                {
                    "Fn::Sub": f"arn:aws:codepipeline:${{AWS::Region}}:${{AWS::AccountId}}:${{{codepipeline_logical_id}}}"
                }
            ],
        )
    ]

    return ResourceOutput(
        definition={
            **generate_role(
                "CloudWatchEventsRole",
                "events.amazonaws.com",
                ["CloudWatchEventsPolicy"],
            ),
            **generate_managed_policy("CloudWatchEventsPolicy", permissions),
        },
        logical_id="CloudWatchEventsRole",
    )
