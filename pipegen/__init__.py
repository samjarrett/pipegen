import pkg_resources

PACKAGE_NAME = "pipegen"
try:
    VERSION = pkg_resources.get_distribution(PACKAGE_NAME).version
except pkg_resources.DistributionNotFound:
    VERSION = "dev"
