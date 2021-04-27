from pipegen.config import contains_codecommit_with_event

from . import codebuild, codepipeline, iam, logs


def generate(config):
    """Generate all config elements"""

    resources = {}

    log_group = logs.log_group(config)
    log_group_logical_id = None
    if log_group:
        resources.update(log_group.definition)
        log_group_logical_id = log_group.logical_id

    definition, codebuild_role_logical_name = iam.codebuild_role(
        config, log_group_logical_id
    )
    resources.update(definition)

    codebuild_projects = codebuild.get_codebuild_projects(config)
    codebuild_logical_ids = []
    for codebuild_project in codebuild_projects:
        definition, codebuild_project_logical_name = codebuild.project(
            codebuild_project,
            config.get("config", {}),
            codebuild_role_logical_name,
            log_group_logical_id,
        )

        resources.update(definition)
        codebuild_logical_ids.append(codebuild_project_logical_name)

    definition, codepipeline_role_logical_name = iam.codepipeline_role(
        config, codebuild_logical_ids
    )
    resources.update(definition)

    definition, codepipeline_logical_id = codepipeline.pipeline(
        config, codepipeline_role_logical_name
    )
    resources.update(definition)

    if contains_codecommit_with_event(config):
        definition, cloudwatch_event_role = iam.cloud_watch_event_role(
            codepipeline_logical_id
        )
        resources.update(definition)
        definition, _ = codepipeline.cloudwatch_events(
            config, cloudwatch_event_role, codepipeline_logical_id
        )
        resources.update(definition)

    return resources
