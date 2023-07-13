#!/usr/bin/python
# SPDX-License-Identifier: BSD-2-Clause
# vim:ts=4:sw=4:et
#
# Copyright (c) 2022-2023 Valve Software
# Maintainer: Vicki Pfau <vi@endrift.com>
from ds_inhibit import Inhibitor, logger
import glob
import logging
import os

logger.setLevel(logging.DEBUG)


def do_assert(*args, **kwargs):
    assert False


def test_get_nodes_no_nodes(monkeypatch):
    monkeypatch.setattr(glob, 'glob', lambda _: [])
    assert Inhibitor.get_nodes(0) == []


def test_get_nodes_no_mice(monkeypatch):
    def fake_glob(g):
        if g.endswith('input*'):
            return ['/id']
        if g.endswith('mouse*'):
            assert g == '/id/mouse*'
            return []
        assert False

    monkeypatch.setattr(glob, 'glob', fake_glob)
    assert Inhibitor.get_nodes(0) == []


def test_get_nodes_yes_mice(monkeypatch):
    def fake_glob(g):
        if g.endswith('input*'):
            return ['/id']
        if g.endswith('mouse*'):
            assert g == '/id/mouse*'
            return ['/id/mouse0']
        assert False

    monkeypatch.setattr(glob, 'glob', fake_glob)
    assert Inhibitor.get_nodes(0) == ['/id/inhibited']


def test_get_nodes_raise(monkeypatch):
    def do_raise(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(glob, 'glob', do_raise)
    assert Inhibitor.get_nodes(0) == []


def test_can_inhibit_no_driver(monkeypatch):
    def do_raise(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr(os, 'readlink', do_raise)
    monkeypatch.setattr(Inhibitor, 'get_nodes', do_assert)

    assert Inhibitor.can_inhibit(0) is False


def test_can_inhibit_drivers(monkeypatch):
    class MockException(Exception):
        pass

    def do_raise(*args, **kwargs):
        raise MockException

    monkeypatch.setattr(Inhibitor, 'get_nodes', do_raise)

    monkeypatch.setattr(os, 'readlink', lambda _: 'hid/sony')
    try:
        assert Inhibitor.can_inhibit(0) is not False
    except MockException:
        pass

    monkeypatch.setattr(os, 'readlink', lambda _: 'hid/playstation')
    try:
        assert Inhibitor.can_inhibit(0) is not False
    except MockException:
        pass

    monkeypatch.setattr(os, 'readlink', lambda _: 'hid/hidraw')
    try:
        assert Inhibitor.can_inhibit(0) is False
    except MockException:
        assert False


def test_can_inhibit_no_nodes(monkeypatch):
    monkeypatch.setattr(os, 'readlink', lambda _: 'hid/sony')
    monkeypatch.setattr(os, 'access', do_assert)
    monkeypatch.setattr(Inhibitor, 'get_nodes', lambda _: [])
    assert Inhibitor.can_inhibit(0) is False


def test_can_inhibit_nodes_no_write(monkeypatch):
    monkeypatch.setattr(os, 'readlink', lambda _: 'hid/sony')
    monkeypatch.setattr(os, 'access', lambda a, b: False)
    monkeypatch.setattr(Inhibitor, 'get_nodes', lambda _: ['/sys/inhibited'])
    assert Inhibitor.can_inhibit(0) is False


def test_can_inhibit_nodes_yes_write(monkeypatch):
    monkeypatch.setattr(os, 'readlink', lambda _: 'hid/sony')
    monkeypatch.setattr(os, 'access', lambda a, b: True)
    monkeypatch.setattr(Inhibitor, 'get_nodes', lambda _: ['/sys/inhibited'])
    assert Inhibitor.can_inhibit(0) is True
