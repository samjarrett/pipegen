from typing import Any, Iterable, NamedTuple, Optional, TypedDict, Union

from pipegen.config import FnGetAtt, FnSub, Ref, get_ecr_arn, parse_value

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
    Action: list[str]
    Resource: list[Union[str, FnSub, FnGetAtt, Ref]]


class IAMResourceOutput(NamedTuple):
    """An IAM Resource's output"""

    definition: dict[str, Any]
    role_logical_id: str


def iam_permission(
    action: list[str], resource: list[Union[str, FnSub, FnGetAtt, Ref]]
) -> IAMPermissionDict:
    """Return an IAM permission"""
    return {
        "Effect": "Allow",
        "Action": action,
        "Resource": resource,
    }


def get_ecr_arns(image_list: list[Optional[str]]) -> Iterable[str]:
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


def generate_role(resource_name: str, service: str, managed_policies: list[str]):
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


def codepipeline_role(config, codebuild_projects: list[str]) -> IAMResourceOutput:
    """Generate a CodePipeline role + policy resources"""
    sub_config = config.get("config", {})
    permissions = [
        iam_permission(
            S3_BUCKET_PERMISSIONS,
            [
                parse_value(
                    "arn:aws:s3:::${BucketName}",
                    BucketName=str(sub_config.get("s3_bucket", "")),
                ),
                parse_value(
                    "arn:aws:s3:::${BucketName}/*",
                    BucketName=str(sub_config.get("s3_bucket", "")),
                ),
            ],
        ),
        iam_permission(
            KMS_KEY_PERMISSIONS,
            [
                parse_value(
                    "${KmsKeyArn}",
                    KmsKeyArn=sub_config.get("kms_key_arn"),
                )
            ],
        ),
        iam_permission(
            CODEPIPELINE_CODEBUILD_PERMISSIONS,
            [
                {"Fn::GetAtt": [codebuild_project, "Arn"]}
                for codebuild_project in codebuild_projects
            ],
        ),
    ]

    return IAMResourceOutput(
        definition={
            **generate_role(
                "CodePipelineRole", "codepipeline.amazonaws.com", ["CodePipelinePolicy"]
            ),
            **generate_managed_policy("CodePipelinePolicy", permissions),
        },
        role_logical_id="CodePipelineRole",
    )


def codebuild_role(config) -> IAMResourceOutput:
    """Generate a CodeBuild role + policy resources"""
    sub_config = config.get("config", {})
    permissions = []

    # Add CW Logs perms
    log_group = sub_config.get("codebuild", {}).get("log_group", {})
    if log_group.get("enabled", False):
        permissions.append(
            iam_permission(
                ["logs:CreateLogStream", "logs:PutLogEvents"],
                [
                    parse_value(
                        "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:${LogGroupName}",
                        LogGroupName=log_group.get("name", ""),
                    ),
                    parse_value(
                        "arn:aws:logs:${AWS::Region}:${AWS::AccountId}:log-group:${LogGroupName}:log-stream:*",
                        LogGroupName=log_group.get("name", ""),
                    ),
                ],
            )
        )

    # Add Source perms
    codecommit_projects: list[Union[str, FnSub, FnGetAtt, Ref]] = []
    for _, source in config.get("sources", {}).items():
        if source.get("from", "").lower() == "codecommit":
            codecommit_projects.append(
                parse_value(
                    "arn:aws:codecommit:${AWS::Region}:${AWS::AccountId}:${RepositoryName}",
                    Region=source.get("region", "AWS::Region"),
                    AccountId=source.get("account_id", "AWS::AccountId"),
                    RepositoryName=source.get("repository"),
                )
            )
        else:
            raise NotImplementedError(
                f"Source type '{source.get('from', '')}' is not supported yet"
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

    default_image = sub_config.get("codebuild", {}).get("image")
    images = set()
    for stage in config.get("stages", []):
        for action in stage.get("actions", []):
            images.add(action.get("image", default_image))

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
                S3_BUCKET_PERMISSIONS,
                [
                    parse_value(
                        "arn:aws:s3:::${BucketName}",
                        BucketName=sub_config.get("s3_bucket"),
                    ),
                    parse_value(
                        "arn:aws:s3:::${BucketName}/*",
                        BucketName=sub_config.get("s3_bucket"),
                    ),
                ],
            ),
            iam_permission(
                KMS_KEY_PERMISSIONS,
                [
                    parse_value(
                        "${KmsKeyArn}",
                        KmsKeyArn=sub_config.get("kms_key_arn"),
                    )
                ],
            ),
        ]
    )

    # Add any additionally specified IAM perms
    iam = sub_config.get("iam")
    if iam:
        permissions.extend(iam)

    return IAMResourceOutput(
        definition={
            **generate_role(
                "CodeBuildRole", "codebuild.amazonaws.com", ["CodeBuildPolicy"]
            ),
            **generate_managed_policy("CodeBuildPolicy", permissions),
        },
        role_logical_id="CodeBuildRole",
    )
