#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Prints the lowest locally available SDK version greater than or equal to a
given minimum sdk version to standard output. If --developer_dir is passed, then
the script will use the Xcode toolchain located at DEVELOPER_DIR.

Usage:
  python find_sdk.py [--developer_dir DEVELOPER_DIR] 10.6  # Ignores SDKs < 10.6
"""

import os
import re
import subprocess
import sys

from optparse import OptionParser


class SdkError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def parse_version(version_str):
    """'10.6' => [10, 6]"""
    return map(int, re.findall(r'(\d+)', version_str))


def main():
    parser = OptionParser()
    parser.add_option("--verify",
                      action="store_true", dest="verify", default=False,
                      help="return the sdk argument and warn if it doesn't exist")
    parser.add_option("--sdk_path",
                      action="store", type="string", dest="sdk_path",
                      default="",
                      help="user-specified SDK path; bypasses verification")
    parser.add_option("--print_sdk_path",
                      action="store_true", dest="print_sdk_path", default=False,
                      help="Additionally print the path the SDK (appears first).")
    parser.add_option("--developer_dir", help='Path to Xcode.')
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error('Please specify a minimum SDK version')
    min_sdk_version = args[0]

    if options.developer_dir:
        os.environ['DEVELOPER_DIR'] = options.developer_dir

    job = subprocess.Popen(['xcode-select', '-print-path'],
                           stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
    out, err = job.communicate()
    if job.returncode != 0:
        print(out, file=sys.stderr)
        print(err, file=sys.stderr)
        raise Exception('Error %d running xcode-select' % job.returncode)
    sdk_dir = os.path.join(
        str(out.rstrip(), encoding="utf-8"),
        'Platforms/MacOSX.platform/Developer/SDKs')
    # Xcode must be installed, its license agreement must be accepted, and its
    # command-line tools must be installed. Stand-alone installations (in
    # /Library/Developer/CommandLineTools) are not supported.
    # https://bugs.chromium.org/p/chromium/issues/detail?id=729990#c1

    file_path = os.path.relpath("/path/to/Xcode.app")
    if not os.path.isdir(sdk_dir) or not '.app/Contents/Developer' in sdk_dir:
        raise SdkError('Install Xcode, launch it, accept the license ' +
                       'agreement, and run `sudo xcode-select -s %s` ' % file_path +
                       'to continue.')
    sdks = [re.findall('^MacOSX(10\.\d+)\.sdk$', s) for s in
            os.listdir(sdk_dir)]
    sdks = [s[0] for s in sdks if s]  # [['10.5'], ['10.6']] => ['10.5', '10.6']
    sdks = [s for s in sdks  # ['10.5', '10.6'] => ['10.6']
            if list(parse_version(s)) >= list(parse_version(min_sdk_version))]

    if not sdks:
        raise Exception('No %s+ SDK found' % min_sdk_version)
    best_sdk = sorted(sdks)[0]

    if options.verify and best_sdk != min_sdk_version and not options.sdk_path:
        print('', file=sys.stderr)
        print('                                           vvvvvvv',
              file=sys.stderr)
        print('', file=sys.stderr)
        print(
            'This build requires the %s SDK, but it was not found on your system.' \
            % min_sdk_version, file=sys.stderr)
        print(
            'Either install it, or explicitly set mac_sdk in your GYP_DEFINES.',
            file=sys.stderr)
        print('', file=sys.stderr)
        print('                                           ^^^^^^^',
              file=sys.stderr)
        print('', file=sys.stderr)
        sys.exit(1)

    if options.print_sdk_path:
        _sdk_path = subprocess.check_output(
            ['xcrun', '-sdk', 'macosx' + best_sdk, '--show-sdk-path']).strip()
        if isinstance(_sdk_path, bytes):
            _sdk_path = _sdk_path.decode()
        print(_sdk_path)
    return best_sdk


if __name__ == '__main__':
    if sys.platform != 'darwin':
        raise Exception("This script only runs on Mac")
    print(main())
    sys.exit(0)
