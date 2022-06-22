# This file is part of cjdk.
# Copyright 2022, Board of Regents of the University of Wisconsin System
# SPDX-License-Identifier: MIT

import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from cjdk import _cache
from cjdk._cache import atomic_file


_TEST_URL = "http://x.com/y"


def test_atomic_file_uncached(tmp_path):
    def fetch(path, **kwargs):
        path.touch()
        assert path.samefile(
            tmp_path
            / "v0"
            / "fetching"
            / "p"
            / _cache._key_for_url(_TEST_URL)
            / "testfile"
        )

    cached = atomic_file(
        "p", _TEST_URL, "testfile", fetch, cache_dir=tmp_path, ttl=2**63
    )
    assert cached.is_file()
    assert cached.samefile(
        tmp_path / "v0" / "p" / _cache._key_for_url(_TEST_URL) / "testfile"
    )
    assert (cached.parent.parent / (cached.parent.name + ".url")).is_file()
    with open(cached.parent.parent / (cached.parent.name + ".url")) as f:
        assert f.read() == _TEST_URL


def test_atomic_file_cached(tmp_path):
    def fetch(path, **kwargs):
        assert False

    keydir = tmp_path / "v0" / "p" / _cache._key_for_url(_TEST_URL)
    keydir.mkdir(parents=True)
    (keydir / "testfile").touch()
    mtime = (keydir / "testfile").stat().st_mtime
    cached = atomic_file(
        "p", _TEST_URL, "testfile", fetch, cache_dir=tmp_path, ttl=2**63
    )
    assert cached.is_file()
    assert cached.samefile(keydir / "testfile")
    assert (keydir / "testfile").stat().st_mtime == mtime


def test_atomic_file_expired(tmp_path):
    new_mtime = 0

    def fetch(path, **kwargs):
        path.touch()
        assert path.samefile(
            tmp_path
            / "v0"
            / "fetching"
            / "p"
            / _cache._key_for_url(_TEST_URL)
            / "testfile"
        )
        nonlocal new_mtime
        new_mtime = path.stat().st_mtime

    keydir = tmp_path / "v0" / "p" / _cache._key_for_url(_TEST_URL)
    keydir.mkdir(parents=True)
    (keydir / "testfile").touch()
    old_mtime = (keydir / "testfile").stat().st_mtime
    time.sleep(0.1)
    cached = atomic_file(
        "p", _TEST_URL, "testfile", fetch, ttl=0.05, cache_dir=tmp_path
    )
    assert new_mtime > old_mtime
    assert cached.is_file()
    assert cached.samefile(keydir / "testfile")
    assert (keydir / "testfile").stat().st_mtime == new_mtime


def test_atomic_file_fetching_elsewhere(tmp_path):
    exec = ThreadPoolExecutor()

    def fetch(path, **kwargs):
        assert False

    keydir = tmp_path / "v0" / "p" / _cache._key_for_url(_TEST_URL)
    keydir.mkdir(parents=True)
    (keydir / "testfile").touch()

    def other_fetch():
        def fetch(path, **kwargs):
            time.sleep(0.1)
            with open(path, "w") as f:
                f.write("other")

        atomic_file(
            "p", _TEST_URL, "testfile", fetch, ttl=0, cache_dir=tmp_path
        )

    exec.submit(other_fetch)
    time.sleep(0.05)
    cached = atomic_file(
        "p", _TEST_URL, "testfile", fetch, ttl=0, cache_dir=tmp_path
    )
    assert cached.is_file()
    with open(cached) as f:
        assert f.read() == "other"

    exec.shutdown()


def test_atomic_file_fetching_elsewhere_timeout(tmp_path):
    def fetch(path, **kwargs):
        assert False

    (
        tmp_path / "v0" / "fetching" / "p" / _cache._key_for_url(_TEST_URL)
    ).mkdir(parents=True)

    with pytest.raises(Exception):
        atomic_file(
            "p",
            _TEST_URL,
            "testfile",
            fetch,
            timeout_for_fetch_elsewhere=0.1,
            cache_dir=tmp_path,
            ttl=2**63,
        )


def test_atomic_file_open_elsewhere(tmp_path):
    exec = ThreadPoolExecutor()

    def fetch(path, **kwargs):
        with open(path, "w") as f:
            f.write("new")

    keydir = tmp_path / "v0" / "p" / _cache._key_for_url(_TEST_URL)
    keydir.mkdir(parents=True)
    (keydir / "testfile").touch()

    def close_after_delay(f):
        time.sleep(0.1)
        f.close()

    with open(keydir / "testfile") as fp:
        exec.submit(close_after_delay, fp)
        cached = atomic_file(
            "p", _TEST_URL, "testfile", fetch, ttl=0, cache_dir=tmp_path
        )
        assert cached.is_file()
        with open(keydir / "testfile") as fp2:
            assert fp2.read() == "new"

    exec.shutdown()


@pytest.mark.skipif(
    sys.platform != "win32", reason="applicable only to Windows"
)
def test_atomic_file_open_elsewhere_timeout(tmp_path):
    wrote_new = False

    def fetch(path, **kwargs):
        with open(path, "w") as f:
            f.write("new")
            nonlocal wrote_new
            wrote_new = True

    keydir = tmp_path / "v0" / "p" / _cache._key_for_url(_TEST_URL)
    keydir.mkdir(parents=True)
    (keydir / "testfile").touch()

    with open(keydir / "testfile") as fp:
        with pytest.raises(Exception):
            atomic_file(
                "p",
                _TEST_URL,
                "testfile",
                fetch,
                ttl=0,
                timeout_for_read_elsewhere=0.1,
                cache_dir=tmp_path,
            )

        assert wrote_new
