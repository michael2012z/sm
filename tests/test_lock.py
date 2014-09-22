import unittest
import mock
import os
import gc
import errno

import testlib

import lock


class FailingOpenContext(testlib.TestContext):
    def fake_open(self, fname, mode='r'):
        raise IOError()


class TestLock(unittest.TestCase):
    @testlib.with_context
    def test_lock_without_namespace_creates_nil_namespace(self, context):
        lck = lock.Lock('somename')

        self.assertTrue(
            os.path.exists(
                os.path.join(lck.BASE_DIR, '.nil')))

    @testlib.with_context
    def test_lock_with_namespace_creates_namespace(self, context):
        lck = lock.Lock('somename', ns='namespace')

        self.assertTrue(
            os.path.exists(
                os.path.join(lck.BASE_DIR, 'namespace')))

    @testlib.with_context
    def test_lock_without_namespace_creates_file(self, context):
        lck = lock.Lock('somename')

        self.assertTrue(
            os.path.exists(
                os.path.join(lck.BASE_DIR, '.nil', 'somename')))

    @testlib.with_context
    def test_lock_with_namespace_creates_file(self, context):
        lck = lock.Lock('somename', ns='namespace')

        self.assertTrue(
            os.path.exists(
                os.path.join(lck.BASE_DIR, 'namespace', 'somename')))

    @testlib.with_context
    def test_lock_file_create_fails_retried(self, context):
        Lock = create_lock_class_that_fails_to_create_file(1)
        lck = Lock('somename', ns='namespace')

        self.assertTrue(
            os.path.exists(
                os.path.join(lck.BASE_DIR, 'namespace', 'somename')))


def create_lock_class_that_fails_to_create_file(number_of_failures):

    class LockThatFailsToCreateFile(lock.Lock):
        _failures = number_of_failures

        def _open_lockfile(self):
            if self._failures > 0:
                error = IOError('No such file')
                error.errno = errno.ENOENT
                self._failures -= 1
                raise error
            return lock.Lock._open_lockfile(self)

    return LockThatFailsToCreateFile


class TestLockDestruction(unittest.TestCase):
    def setUp(self):
        gc.collect()
        locks = self.retrieve_lock_instances_from_gc()
        assert 0 == len(locks)
        gc.disable()

    @testlib.with_custom_context(FailingOpenContext)
    def test_close_if_open_failed(self, ctx):
        try:
            lck = lock.Lock('somename')
            raise AssertionError('An IOError was expected here')
        except IOError:
            pass

        locks = self.retrieve_lock_instances_from_gc()
        self.assertEquals(1, len(locks))

        lck, = locks

        lck._close()

    def retrieve_lock_instances_from_gc(self):
        locks = []
        for obj in gc.get_objects():
            if isinstance(obj, lock.Lock):
                locks.append(obj)

        return locks

    def tearDown(self):
        gc.enable()