'''
Tests for the 'core' module.
'''

import unittest
import release

class TestStep(unittest.TestCase):
    '''
    Tests for the main logic of the Step class.
    '''

    @classmethod
    def test_success(cls):
        '''
        A release step that always succeeds.
        '''
        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: True,
            expected={},
            action=lambda: None,
            rollback_action=lambda: None,
        )
        step.execute()

    def test_failure_check(self):
        '''
        A release step that always fails on the check phase.
        '''
        def check():
            raise Exception

        step = release.Step(
            name='success',
            check=check,
            precondition=lambda _: True,
            expected={},
            action=lambda: None,
            rollback_action=lambda: None,
        )
        try:
            step.execute()
        except release.ExecutionError as exception:
            self.assertEqual(exception.phase, release.Phase.CHECK_INITIAL)

    def test_failure_action(self):
        '''
        A release step that always fails on the action phase.
        '''
        def action():
            raise Exception

        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: True,
            expected={},
            action=action,
            rollback_action=lambda: None,
        )
        try:
            step.execute()
        except release.ExecutionError as exception:
            self.assertEqual(exception.phase, release.Phase.EXECUTE)

    def test_failure_rollback_action(self):
        '''
        A release step that always fails on the rollback phase.
        '''
        def rollback_action():
            raise Exception

        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: True,
            expected={},
            action=lambda: None,
            rollback_action=rollback_action,
        )
        try:
            step.execute()
        except release.ExecutionError as exception:
            self.assertEqual(exception.phase, release.Phase.ROLLBACK)

    def test_failure_precondition(self):
        '''
        A release step that always fails on the precondition phase.
        '''

        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: False,
            expected={},
            action=lambda: None,
            rollback_action=lambda: None,
        )
        self.assertRaises(release.PreconditionError, step.execute)

    def test_failure_postcondition(self):
        '''
        A release step that always fails on the postcondition phase.
        '''

        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: True,
            expected={'a':1},
            action=lambda: None,
            rollback_action=lambda: None,
        )
        self.assertRaises(release.PostconditionError, step.execute)

class TestRelease(unittest.TestCase):
    '''
    Tests for the main logic of the Release class.
    '''

    @classmethod
    def test_success(cls):
        '''
        A release that always succeeds.
        '''
        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: True,
            expected={},
            action=lambda: None,
            rollback_action=lambda: None,
        )
        rel = release.Release(
            name='test',
            steps=[step]
        )
        rel.execute()

    def test_failure_action(self):
        '''
        A release that always fails on the action phase.
        '''
        def action():
            raise Exception

        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: True,
            expected={},
            action=action,
            rollback_action=lambda: None,
        )
        rel = release.Release(
            name='test',
            steps=[step]
        )
        try:
            rel.execute()
        except release.ExecutionError:
            self.assertEqual(len(rel.executed_steps), 0)

    def test_failure_rollback_action(self):
        '''
        A release that always fails on the rollback phase.
        '''
        def rollback_action():
            raise Exception

        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: True,
            expected={},
            action=lambda: None,
            rollback_action=rollback_action,
        )
        rel = release.Release(
            name='test',
            steps=[step]
        )
        try:
            rel.execute()
        except release.ExecutionError:
            self.assertEqual(len(rel.executed_steps), 1)


    def test_failure_precondition(self):
        '''
        A release that always fails on the precondition phase.
        '''

        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: False,
            expected={},
            action=lambda: None,
            rollback_action=lambda: None,
        )
        rel = release.Release(
            name='test',
            steps=[step]
        )
        try:
            rel.execute()
        except release.PreconditionError:
            self.assertEqual(len(rel.executed_steps), 0)


    def test_failure_postcondition(self):
        '''
        A release that always fails on the postcondition phase.
        '''

        step = release.Step(
            name='success',
            check=lambda: {},
            precondition=lambda _: True,
            expected={'a':1},
            action=lambda: None,
            rollback_action=lambda: None,
        )
        rel = release.Release(
            name='test',
            steps=[step]
        )
        try:
            rel.execute()
        except release.PostconditionError:
            self.assertEqual(len(rel.executed_steps), 1)
