"""
These commands are used to build the pacakge repository files.
"""
# pylint: disable=resource-leakage,broad-except
from __future__ import annotations

import logging
import pathlib
import textwrap

from ptscripts import Context, command_group

log = logging.getLogger(__name__)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Define the command group
pkg = command_group(
    name="pkg-repo", help="Packaging Repository Related Commands", description=__doc__
)


@pkg.command(
    name="deb",
    arguments={
        "salt_version": {
            "help": (
                "The salt version for which to build the repository configuration files. "
                "If not passed, it will be discovered by running 'python3 salt/version.py'."
            ),
        },
        "distro": {
            "help": "The debian based distribution to build the repository for",
            "choices": ("debian", "ubuntu"),
        },
        "distro_version": {
            "help": "The distro version.",
        },
        "distro_arch": {
            "help": "The distribution architecture",
            "choices": ("amd64", "arm64"),
        },
        "dev_build": {
            "help": "Developement repository target",
        },
        "repo_path": {
            "help": "Path where the repository shall be created.",
        },
        "key_id": {
            "help": "The GnuPG key ID used to sign.",
        },
        "incoming": {
            "help": (
                "The path to the directory containing the files that should added to "
                "the repository."
            )
        },
    },
)
def debian(
    ctx: Context,
    salt_version: str,
    distro: str,
    distro_version: str,
    key_id: str,
    incoming: pathlib.Path,
    repo_path: pathlib.Path,
    distro_arch: str = "amd64",
    dev_build: bool = False,
):
    """
    Create the debian repository.
    """
    distro_info = {
        "debian": {
            "10": {
                "label": "deb10ary",
                "codename": "buster",
                "suitename": "oldstable",
                "arm_support": False,
            },
            "11": {
                "label": "deb11ary",
                "codename": "bullseye",
                "suitename": "stable",
                "arm_support": True,
            },
        },
        "ubuntu": {
            "18.04": {
                "label": "salt_ubuntu1804",
                "codename": "bionic",
                "arm_support": False,
            },
            "20.04": {
                "label": "salt_ubuntu2004",
                "codename": "focal",
                "arm_support": True,
            },
            "22.04": {
                "label": "salt_ubuntu2204",
                "codename": "jammy",
                "arm_support": True,
            },
        },
    }
    display_name = f"{distro.capitalize()} {distro_version}"
    if distro_version not in distro_info[distro]:
        ctx.error(f"Support for {display_name} is missing.")
        ctx.exit(1)

    distro_details = distro_info[distro][distro_version]
    if distro_arch == "arm64" and not distro_details["arm_support"]:
        ctx.error(f"There's no arm64 support for {display_name}.")
        ctx.exit(1)

    ftp_archive_config_suite = ""
    if distro == "debian":
        ftp_archive_config_suite = f"""\n    APT::FTPArchive::Release::Suite "{distro_details['suitename']}";\n"""
    archive_description = f"SaltProject {display_name} Python 3{'' if dev_build else ' development'} Salt package repo"
    ftp_archive_config = f"""\
    APT::FTPArchive::Release::Origin "SaltProject";
    APT::FTPArchive::Release::Label "{distro_details['label']}";{ftp_archive_config_suite}
    APT::FTPArchive::Release::Codename "{distro_details['codename']}";
    APT::FTPArchive::Release::Architectures "{distro_arch}";
    APT::FTPArchive::Release::Components "main";
    APT::FTPArchive::Release::Description "{archive_description}";
    APT::FTPArchive::Release::Acquire-By-Hash "yes";
    Dir {{
        ArchiveDir ".";
    }};
    BinDirectory "pool" {{
        Packages "dists/{distro_details['codename']}/main/binary-{distro_arch}/Packages";
        Sources "dists/{distro_details['codename']}/main/source/Sources";
        Contents "dists/{distro_details['codename']}/main/Contents-{distro_arch}";
    }}
    """
    repo_path.mkdir(exist_ok=True, parents=True)
    ftp_archive_config_file = repo_path / "apt-ftparchive.conf"
    ftp_archive_config_file.write_text(textwrap.dedent(ftp_archive_config))
