# emacs: -*- mode: python; py-indent-offset: 4; indent-tabs-mode: nil -*-
# vi: set ft=python sts=4 ts=4 sw=4 et:
#
# Copyright 2021 The NiPreps Developers <nipreps@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# We support and encourage derived works from this project, please read
# about our expectations at
#
#     https://www.nipreps.org/community/licensing/
#
"""Runtime checks for data loading without pkg_resources."""

import ast
import builtins
import importlib
import sys
from pathlib import Path


def test_import_and_resource_loading_without_pkg_resources(monkeypatch):
    """Ensure niworkflows can import and access packaged resources without pkg_resources."""

    def _guarded_import(name, *args, **kwargs):
        if name == 'pkg_resources' or name.startswith('pkg_resources.'):
            raise ModuleNotFoundError("No module named 'pkg_resources'")
        return original_import(name, *args, **kwargs)

    original_import = builtins.__import__
    monkeypatch.setattr(builtins, '__import__', _guarded_import)

    sys.modules.pop('pkg_resources', None)
    sys.modules.pop('niworkflows', None)
    sys.modules.pop('niworkflows.data', None)

    niworkflows = importlib.import_module('niworkflows')
    data = importlib.import_module('niworkflows.data')

    assert data.load('nipreps.json').is_file()
    assert (niworkflows.load_resource('reports') / 'report.tpl').is_file()


def test_no_pkg_resources_imports_under_package():
    """Prevent regressions reintroducing pkg_resources imports in niworkflows package code."""

    package_root = Path(__file__).resolve().parents[1]
    offenders = []

    for pyfile in package_root.rglob('*.py'):
        tree = ast.parse(pyfile.read_text(), filename=str(pyfile))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(
                    f'{pyfile}:{node.lineno}'
                    for alias in node.names
                    if alias.name == 'pkg_resources' or alias.name.startswith('pkg_resources.')
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                if node.module == 'pkg_resources' or node.module.startswith('pkg_resources.'):
                    offenders.append(f'{pyfile}:{node.lineno}')

    assert not offenders, f'pkg_resources imports found: {", ".join(sorted(offenders))}'
