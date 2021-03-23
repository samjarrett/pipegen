from . import codebuild, codepipeline, iam, logs


def generate(config):
    """Generate all config elements"""

    resources = {}

    log_group = logs.log_group(config)
    if log_group:
        resources.update(log_group.definition)

    definition, codebuild_role_logical_name = iam.codebuild_role(config)
    resources.update(definition)

    codebuild_projects = codebuild.get_codebuild_projects(config)
    codebuild_logical_ids = []
    for codebuild_project in codebuild_projects:
        definition, codebuild_project_logical_name = codebuild.project(
            codebuild_project,
            config.get("config", {}),
            codebuild_role_logical_name,
        )

        resources.update(definition)
        codebuild_logical_ids.append(codebuild_project_logical_name)

    definition, codepipeline_role_logical_name = iam.codepipeline_role(
        config, codebuild_logical_ids
    )
    resources.update(definition)

    definition, _ = codepipeline.pipeline(config, codepipeline_role_logical_name)
    resources.update(definition)

    return resources
