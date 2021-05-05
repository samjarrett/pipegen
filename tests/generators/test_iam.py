from pipegen.generators import iam


def test_iam_permission():
    """Tests iam_permission()"""
    assert iam.iam_permission(["iam:*", "something:*"], ["*"]) == {
        "Effect": "Allow",
        "Action": ["iam:*", "something:*"],
        "Resource": ["*"],
    }


def test_get_ecr_arns():
    """Tests get_ecr_arns()"""
    arns = list(
        iam.get_ecr_arns(
            [
                "123456789012.dkr.ecr.us-east-1.amazonaws.com/repo",
                "123456789012.dkr.ecr.us-west-2.amazonaws.com/repo",
                "something-else",  # this one should be discarded entirely
            ]
        )
    )
    assert arns == [
        "arn:aws:ecr:us-east-1:123456789012:repository/repo",
        "arn:aws:ecr:us-west-2:123456789012:repository/repo",
    ]


def test_generate_managed_policy():
    """Tests generate_managed_policy()"""
    assert iam.generate_managed_policy("MyResource", "This is my permission") == {
        "MyResource": {
            "Type": "AWS::IAM::ManagedPolicy",
            "Properties": {
                "PolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": "This is my permission",
                }
            },
        }
    }


def test_generate_role():
    """Tests generate_role()"""
    assume_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "service"},
                "Action": "sts:AssumeRole",
            }
        ],
    }
    assert iam.generate_role("MyRole", "service", ["policy1", "policy2"]) == {
        "MyRole": {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": assume_policy,
                "ManagedPolicyArns": [{"Ref": "policy1"}, {"Ref": "policy2"}],
            },
        }
    }
