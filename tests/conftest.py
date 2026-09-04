#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Shared fixtures for the MDK test suite.

The tests do not require a real Moodle checkout or database. The `instance`
fixture builds a fake Moodle instance straight on disk (with a minimal
lib/components.json) so that plugin and component path resolution can be
exercised deterministically.
"""

import json
import os

import pytest


class FakeMoodle:
    def __init__(self, path, admin='admin'):
        self.path = str(path)
        self._admin = admin

    def get(self, name, default=None):
        return {'path': self.path, 'admin': self._admin}.get(name, default)


@pytest.fixture
def instance(tmp_path):
    def build(plugintypes, subsystems=None, admin='admin'):
        path = tmp_path / 'moodle'
        lib = os.path.join(path, 'lib')
        os.makedirs(lib, exist_ok=True)
        data = {'plugintypes': plugintypes}
        if subsystems is not None:
            data['subsystems'] = subsystems
        with open(os.path.join(lib, 'components.json'), 'w') as f:
            json.dump(data, f)
        return FakeMoodle(path, admin=admin)
    return build


@pytest.fixture
def bare_instance(tmp_path):
    """A FakeMoodle pointing at an empty folder (no components.json yet)."""
    return FakeMoodle(tmp_path / 'moodle')
