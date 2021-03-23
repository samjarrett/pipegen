import click


def split_key_val_pairs(context, parameter, args):  # pylint: disable=unused-argument
    """Split key-value pairs into a dictionary"""
    return dict(arg.split("=") for arg in args)


CONFIG_OPTION = click.option(
    "--config", "config_file", type=click.File("r"), required=True
)
VARS_OPTION = click.option(
    "--var",
    "var_overrides",
    type=str,
    required=False,
    multiple=True,
    callback=split_key_val_pairs,
)
