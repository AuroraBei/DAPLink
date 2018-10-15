#
# DAPLink Interface Firmware
# Copyright (c) 2009-2018, ARM Limited, All Rights Reserved
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
import os
import shutil
import sys
import yaml

from subprocess import check_output, CalledProcessError
from pre_build_script import generate_version_file
from generate_mbedcli_files import generate_mbedcli_files
from post_compute_crc import post_compute_crc
from package_release_files import package_release_files

PROJECTS_YAML = "projects.yaml"
VERSION_YAML = "version.yaml"

def mbedcli_compile(daplink_dir, build_folder, project, toolchain, clean):
    generate_mbedcli_files(os.path.join(daplink_dir, "projects.yaml"), project)
    project_dir=os.path.join(daplink_dir, build_folder, project.upper())
    if clean is True and os.path.exists(project_dir):
        print("Deleting %s" % project_dir)
        shutil.rmtree(project_dir, ignore_errors=True)
    try:
        check_output("mbed compile -m %s -t %s --profile custom_profile.json" % (project, toolchain), shell=True)
        cli_name_out = os.path.basename(daplink_dir)
        build_dir = os.path.join(project_dir, toolchain+"-CUSTOM_PROFILE")
        for file in os.listdir(build_dir):
            if file.startswith(cli_name_out):
                rename_file = os.path.join(build_dir, file.replace(cli_name_out, project, 1))
                if os.path.exists(rename_file):
                    os.remove(rename_file)
                os.rename(os.path.join(build_dir, file), rename_file)
        cli_hex_output = os.path.join(build_dir, project + ".hex")
        crc_file_output = os.path.join(build_dir, project + "_crc")
        post_compute_crc(cli_hex_output, crc_file_output)
    except CalledProcessError:
        print("Error - mbed compile error")
        exit(1)

def main():
    """python -u tools/mbedcli_compile.py kl26z_microbit_if kl26z_bl --clean"""

    #parse project yaml file for project list
    project_list = []
    with open(PROJECTS_YAML, 'r') as top_yaml:
        try:
            topdict = yaml.load(top_yaml)
            for dict_key in topdict:
                if dict_key == 'projects':
                    for project in topdict[dict_key]:
                        project_list.append(project)
                    break
        except yaml.YAMLError as ex:
            print("Found yaml parse error", ex)

    #parse the arguments
    projects = "List of supported projects\n\n" + "\n".join(project_list) #
    parser = argparse.ArgumentParser(description='mbedcli compile support for DAPLink', epilog=projects, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('projects', help='Selectively compile only the firmware specified otherwise all projects',
                        nargs='*', type=str, default=[])
    parser.add_argument('--release', dest='release', action='store_true', help='Create a release with the yaml version file')
    parser.add_argument('--build-folder', type=str, default='BUILD', help='Release directory to grab files from')
    parser.add_argument('--release-folder', type=str, default='firmware', help='Directory to create and place files in')
    parser.add_argument('--toolchain', type=str, default='ARM', help='Toolchain directory if present')
    parser.add_argument('--clean', dest='clean', action='store_true', help='Rebuild or delete build folder before compile')
    parser.set_defaults(clean=False)
    parser.set_defaults(release=False)
    args = parser.parse_args()


    self_path = os.path.abspath(__file__)
    tools_dir = os.path.dirname(self_path)
    daplink_dir = os.path.dirname(tools_dir)
    if os.path.basename(tools_dir) != "tools":
        print("Error - this script must be run from the tools directory")
        exit(-1)
    version_git_dir = os.path.join(daplink_dir, "source", "daplink")
    generate_version_file(version_git_dir)
    if not args.projects == []: 

        for project in args.projects:
            print("Compiling %s" % project)
            mbedcli_compile(daplink_dir, args.build_folder, project, args.toolchain, args.clean)
    else:
        print("compiling all firmware")

        for project in project_list:
            print("Compiling %s" % project)
            mbedcli_compile(daplink_dir, args.build_folder, project, args.toolchain, args.clean)

    if args.release is True:
        release_version = 0
        with open(os.path.join("records","tools", VERSION_YAML), 'r') as ver_yaml:
            try:
                verdict = yaml.load(ver_yaml)
                release_version = int(verdict['common']['macros'][0].split('=')[1])
            except yaml.YAMLError as ex:
                print("Found yaml parse error", ex)

        release_dir = args.release_folder + "_%04i" % release_version 
        if os.path.exists(release_dir):
            print("Deleting %s" % release_dir)
            shutil.rmtree(release_dir, ignore_errors=True)
        print("Releasing directory: " + release_dir)
        toolchain_dir = args.toolchain+"-CUSTOM_PROFILE"
        package_release_files(args.build_folder, release_dir, release_version, toolchain_dir)

main()
