#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for mdk.plugins.PluginManager path resolution.

These tests lock in how plugin type directories are resolved for branches
using and not using the public/ directory introduced in Moodle 5.1 (see
https://github.com/FMCorz/mdk/issues/260). They create a fake instance folder
on disk so that no real Moodle checkout is required.
"""

import json
import os

import pytest

from mdk.plugins import PluginManager, PluginObject


def _make_dirs(root, *rels):
    for rel in rels:
        os.makedirs(os.path.join(root, rel), exist_ok=True)


def _write_json(root, rel, data):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f)


class TestPublicDirectoryResolution:
    def test_plain_plugin_type(self, instance):
        M = instance({'mod': 'public/mod'})
        assert PluginManager.getTypeDirectory('mod', M) == f'{M.path}/public/mod'

    def test_nested_plugin_types(self, instance):
        M = instance({
            'tool': 'public/admin/tool',
            'editor': 'public/lib/editor',
        })
        assert PluginManager.getTypeDirectory('tool', M) == f'{M.path}/public/admin/tool'
        assert PluginManager.getTypeDirectory('editor', M) == f'{M.path}/public/lib/editor'

    def test_no_public_prefix_before_moodle_51(self, instance):
        M = instance({'mod': 'mod', 'tool': 'admin/tool'})
        assert PluginManager.getTypeDirectory('mod', M) == f'{M.path}/mod'
        assert PluginManager.getTypeDirectory('tool', M) == f'{M.path}/admin/tool'

    def test_has_plugin_under_public(self, instance):
        M = instance({'mod': 'public/mod'})
        _make_dirs(M.path, 'public/mod/simplereminder')
        assert PluginManager.hasPlugin(PluginObject('mod_simplereminder'), M) is True
        assert PluginManager.hasPlugin(PluginObject('mod_other'), M) is False

    def test_delete_directory_tree_under_public(self, instance):
        M = instance({'mod': 'public/mod'})
        _make_dirs(M.path, 'public/mod/simplereminder/db')
        plugin = os.path.join(M.path, 'public/mod/simplereminder')
        PluginManager.deleteDirectoryTree(PluginObject('mod_simplereminder'), M)
        assert not os.path.isdir(plugin)

    def test_unknown_plugin_type_from_components_falls_back(self, instance):
        plugintypes = {
            'mod': 'public/mod',
            'editor': 'public/lib/editor',
            'local': 'public/local',
            'tool': 'public/admin/tool',
        }
        M = instance(plugintypes)
        # Create every declared plugintype directory, like a real install.
        for rel in plugintypes.values():
            _make_dirs(M.path, rel)
        # A type not declared in components.json is not known to the static
        # tables either and must raise.
        with pytest.raises(ValueError):
            PluginManager.getTypeDirectory('unknownthing', M)

    def test_missing_components_file_falls_back_to_static_table(self, bare_instance):
        M = bare_instance
        assert PluginManager.getTypeDirectory('mod', M) == f'{M.path}/mod'

    def test_subplugin_type_under_public(self, instance):
        plugintypes = {
            'mod': 'public/mod',
            'editor': 'public/lib/editor',
            'local': 'public/local',
            'tool': 'public/admin/tool',
        }
        M = instance(plugintypes, subsystems={'admin': 'admin', 'lib': 'lib'})
        # Create every declared plugintype directory, like a real install.
        for rel in plugintypes.values():
            _make_dirs(M.path, rel)
        _make_dirs(M.path, 'public/mod/assign/db', 'public/mod/assign/submission')
        _write_json(M.path, 'public/mod/assign/db/subplugins.json', {
            'subplugintypes': {'assignsubmission': 'submission'},
            'plugintypes': {'assignsubmission': 'mod/assign/submission'},
        })
        expected = f'{M.path}/public/mod/assign/submission'
        assert PluginManager.getTypeDirectory('assignsubmission', M) == expected
        assert PluginManager.hasPlugin(PluginObject('assignsubmission_demo'), M) is False

    def test_unexpected_resolver_error_surfaces(self, instance, monkeypatch):
        plugintypes = {
            'mod': 'public/mod',
            'editor': 'public/lib/editor',
            'local': 'public/local',
            'tool': 'public/admin/tool',
        }
        M = instance(plugintypes, subsystems={'admin': 'admin', 'lib': 'lib'})
        for rel in plugintypes.values():
            _make_dirs(M.path, rel)

        class _BoomResolver:
            @property
            def subplugintypes(self):
                raise RuntimeError('unexpected')

        # Only the documented failure modes are caught; a genuine bug is not
        # swallowed by the subplugin resolution fallback.
        monkeypatch.setattr('mdk.plugins.ComponentResolver', lambda *a, **k: _BoomResolver())
        with pytest.raises(RuntimeError):
            PluginManager.getTypeDirectory('assignfoo', M)

    def test_all_relative_return_unchanged(self, instance):
        M = instance({'mod': 'public/mod'})
        assert PluginManager.getTypeDirectory('mod') == '/mod'
