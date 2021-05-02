# pipegen

<div align="center">
  <img height="150px" src="docs/pipe.png" alt="A pixelated pipe">
</div>

A CodePipeline/CodeBuild CI/CD Pipeline creator + deployer.

## Installation

Install using pip/pypi:

```bash
pip install pipegen
```

## Usage

Deploying your pipeline with pipegen:

```bash
pipegen deploy --config CONFIG_FILE --stack-name NAME_OF_STACK [--var KEY=VALUE [--var KEY=VALUE]]
```

To output compiled configuration:

```bash
pipegen dump config --config CONFIG_FILE [--var KEY=VALUE [--var KEY=VALUE]]
```

To output compiled CloudFormation template:

```bash
pipegen dump template --config CONFIG_FILE [--var KEY=VALUE [--var KEY=VALUE]]
```

## Configuration Schema

The schema is broken down into several sections:

- Base/shared config used across many of the resources
- Source configuration
- Pipeline configuration

### Base Config

Base config is used across multiple resources deployed using `pipegen`, or can be used to override some defaults.

Full schema is documented below, required elements are specified with `(R)`, and defaults are indicated.

```yaml
config:
  s3_bucket: (R) the name of a S3 bucket to store artifacts in (source copies, 
             codebuild artifacts, etc)
  kms_key_arn: (R) the ARN of a KMS key to encrypt all resources with

  codepipeline:
    restart_execution_on_update: whether or not to restart an in-progress 
                                 CodePipeline execution if the pipeline is 
                                 updated (default: false)

  codebuild:
    compute_type: the default compute type to use (default: BUILD_GENERAL1_SMALL)
    image: the default docker image to use 
           (default: aws/codebuild/amazonlinux2-x86_64-standard:3.0)
    log_group: 
      enabled: whether or not to enable CloudWatch logs for CodeBuild 
               projects (default: true)
      create: whether or not to create the CloudWatch log group (default: true). 
              Disable if you have created the log group externally.
      name: the name of the CloudWatch log group for the pipeline 
            (default: random generated name based on the stack name)
      retention: A number in days to retain logs (default: null, logs are retained 
                 indefinitely)
  iam: a list of IAM statements to add to the CodeBuild role (default: null). 
       Use if your CodeBuild projects need to manipulate AWS resources
```

#### IAM Examples

By default, `pipegen` configures CodeBuild with the minimal amount of permissions in order to run, decrypt your artifacts from KMS, pull images from ECR (if configured), write logs to CloudWatch logs (if configured).  If you require additional IAM permissions, you can specify them using the following syntax:

```yaml
config:
  iam:
    - standard IAM statement
```

For example, adding permissions to upload files to S3 in your build:

```yaml
config:
  iam:
    - Effect: Allow
      Action:
        - s3:PutObject
      Resource: 
        - my-bucket-name/*
```

### Source configuration

Source configuration defines where your project's code comes from. 

Two top-level options are supported currently:
1. [CodeCommit](https://aws.amazon.com/codecommit/), AWS' hosted git service
2. CodeStar Connections, to use Github.com, GitHub Enterprise (GHE), or BitBucket

Pipelines can use multiple source repositories mixed from either provider. 

#### CodeCommit

The following describes source configuration for using CodeCommit.

Full schema is documented below, required elements are specified with `(R)`, and defaults are indicated.

```yaml
sources:
  - name: (R) a unique name for this source entry
    from: (R) the provider to use. use `CodeCommit` for CodeCommit
    repository: (R) the name of the repository
    branch: (R) the branch to build from
    poll_for_source_changes: whether CodePipeline should poll for updates (default: false)
    event_for_source_changes: whether to use CloudWatch events/EventBridge to 
                              detect updates (default: true)
```

Note: if you want the pipeline to trigger a build when the repository is pushed to, either `poll_for_source_changes` or `event_for_source_changes` should be set to `true` (`event_for_source_changes` is preferred).

#### CodeStar Connections

The following describes source configuration for using CodeStar Connections to get your source from Github.com, GHE or BitBucket.

In order to use CodeStar connections, you must have configurared a connection separately and prior to deploying the pipeline stack. 

Full schema is documented below, required elements are specified with `(R)`, and defaults are indicated.

```yaml
sources:
  - name: (R) a unique name for this source entry
    from: (R) the provider to use. use `CodeCommit` for CodeCommit
    repository: (R) the name of the repository
    branch: (R) the branch to build from
    connection_arn: (R) the codestar connection ARN to use to pull changes through
```

### Pipeline configuration

The following describes the pipeline's build configuration.

Full schema is documented below, required elements are specified with `(R)`, and defaults are indicated.

```yaml
stages:
  - name: (R) a unique name for this deploy stage, e.g. "Build", "Deploy", etc
    enabled: whether or not this stage is enabled (default: true)
    actions:
      - name: (R) a unique name for this action, e.g. "Build", "DeployToStaging", 
              "DeleteProduction", etc
        provider: the provider to use to perform the action, 
                  allowed values: CodeBuild (default: CodeBuild). 
                  Note: list may be extended in future
        buildspec: a path to a CodeBuild buildspec YAML file from your first 
                   repository's root directory
        commands: a list of commands to run as part of your buildspec
        artifacts: a list of file path artifacts to store after your build
        compute_type: the compute type to use (default: config.codebuild.compute_type's value)
        image: the docker image to use (default: config.codebuild.image's value)
        environment: a hash of "key: value" variables to provide to the build
        input_artifacts: a list of other build actions `Name` fields, who's artifacts 
                         to bring in to your build
```

#### BuildSpec / Commands / Artifacts

When using CodeBuild, you can either:
- not specify `buildspec`, `commands`, or `artifacts` fields, which will default to using `buildspec.yml` in the primary source's root directory for build instructions,
- provide a `buildspec` field, to specify a file in your repository that contains build instructions,
- provide `commands` (and `artifacts` if needed) for pipegen to generate a buildspec for you inline.

The template reference for a CodeBuild buildspec can be found here: https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html. If you specify `commands`, pipegen uses buildspec v0.2 to generate a buildspec inline.

#### Environment Variables

By default, pipegen provides two environment variables to your build project:
`AWS_DEFAULT_REGION` and `AWS_REGION`, both are set to the AWS region that you deploy to (CloudFormation equivalent to `AWS::Region`). Either of these can be overridden by specifying those keys with alternative values.

You can provide additional environment variables as needed using the following syntax:

```yaml
environment:
  KEY: VALUE
  MY_VARIABLE: my value
```

#### Input Artifacts

Every CodeBuild project that pipegen configures will have all sources configured added as inputs, meaning that each build will have access to each repository. 

If you are building using a "build then deploy" pattern, you may want to pass build artifacts through to deployment stages. You can achieve this with a syntax similar to the following:

```yaml
stages:
  - name: Build
    actions:
      - name: MyBuildStep
  - name: Deploy
    actions:
      - name: Deploy
        commmands:
          - bin/deploy
        input_artifacts:
          - MyBuildStep # << Note that this matches the action name above
```

### Variables and Imports

`pipegen` supports two special syntaxes for most configuration entries. 

#### Variables

Any `--var key=name` passed to the CLI can be used inside your configuration file, to vary behaviour at runtime using a syntax like `{{vars.KEY}}`. This is commonly used to vary things like the branch used. For example:

`config.yml`:
```yaml
sources:
  - name: Source
    from: CodeCommit
    repository: my-repo
    branch: {{vars.BranchName}}
```

`pipegen cli`:
```bash
pipegen deploy --var BranchName=main ...
```

Further, as configuration for pipegen is evaluated using jinja2, you can use variables to determine other values. Commonly this can be used to enable/disable stages based on branch (e.g. only running a production deploy for the `main` branch).

```yaml
stages:
  - name: Production
    enabled: {{vars.BranchName == "main"}}
```

#### Imports

`pipegen` supports importing values from [CloudFormation exports](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-stack-exports.html) using syntax like `import:ImportName`. 

Example:

```yaml
config:
  s3_bucket: import:S3BucketName
  kms_key_arn: import:KmsKeyArn
```

### Example configuration

#### Building from CodeCommit

```yaml
---
config:
  s3_bucket: my-s3-bucket
  kms_key_arn: arn:aws:kms:REGION:ACCOUNT:key/KEY-ID

sources:
  - name: Source
    from: CodeCommit
    repository: my-repo
    branch: {{vars.BranchName}}

stages:
  - name: Build
    actions:
      - name: Build
        provider: CodeBuild
        buildspec: buildspecs/build.yml
  - name: DevDeploy
    actions:
      - name: Deploy
        provider: CodeBuild
        buildspec: buildspecs/deploy.yml
        environment:
          TARGET_ENVIRONMENT: dev
        input_artifacts:
          - Build
  - name: ProdDeploy
    enabled: {{vars.BranchName == "main"}}
    actions:
      - name: ProdDeploy
        provider: CodeBuild
        buildspec: buildspecs/deploy.yml
        environment:
          TARGET_ENVIRONMENT: prod
        input_artifacts:
          - Build
```

#### Building from CodeStar/Github.com

```yaml
---
config:
  s3_bucket: import:S3BucketName
  kms_key_arn: import:KMSKeyArn
  codebuild:
    log_group:
      retention: 7 # (days)

sources:
  - name: codebuild-test
    from: CodeStarConnection
    repository: samjarrett/codebuild-test
    branch: main
    connection_arn: arn:aws:codestar-connections:REGION:ACCOUNT:connection/CONNECTION-ID

stages:
  - name: Build
    actions:
      - name: Build
        provider: CodeBuild
        commands: 
          - make build
        artifacts:
          - build/*
  - name: Deploy
    actions:
      - name: Deploy
        provider: CodeBuild
        commands:
          - make deploy
        input_artifacts:
          - Build
```
