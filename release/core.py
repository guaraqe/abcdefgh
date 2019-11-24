# pylint: disable=broad-except
# pylint: disable=too-many-arguments
# pylint: disable=too-many-instance-attributes

'''
This module defines a general procedure of release. It is based on
preconditions and postconditions on an observed state. Rollbacks are
automatically performed when necessary.
'''

import traceback
import subprocess
import sys

from enum import Enum, auto
from io import StringIO
from termcolor import colored

################################################################################
# Release steps

class Step:
    '''
    A single step of the release process. It defines:

    - the name of the release step;
    - how to check relevant state of the system at a given moment;
    - what is the precondition on this state for executing the step;
    - how to execute the step;
    - what is the expected state of the system;
    - how to rollback in case of the system being in an unexpected state.

    A lawful instantiation of this class has the following properties:

    - the only functions that have side effects are 'check', 'action' and
      'rollback_action';

    - the 'action' function must be atomic; that is, if it fails, the system
      remains in the initial state.

    The implementation of steps is supposed to take the form of a subclass, so
    that it can use the initial and expected state values for the execution of
    'action' and 'rollback_action'.
    '''

    def __init__(
            self,
            name,
            check,
            precondition,
            expected,
            action,
            rollback_action,
        ):

        self.name = name
        self.precondition = precondition
        self.expected = expected

        # We distinguish the 'check' functions by the exceptions they throw.
        # Failure at different stages demand different rollbacks.
        self.check_initial = self.wrap(Phase.CHECK_INITIAL, check)
        self.check_final = self.wrap(Phase.CHECK_FINAL, check)
        self.check_rollback = self.wrap(Phase.CHECK_ROLLBACK, check)

        # Actions exceptions are wrapped with more information about the step.
        self.action = self.wrap(Phase.EXECUTE, action)
        self.rollback_action = self.wrap(Phase.ROLLBACK, rollback_action)

        # Initial state for the step execution.
        self.initial = None

        # This will always be set by the 'Release' class, but we put a valid
        # value by default.
        self.stdout = sys.stdout

    # Main methods of the class.

    def execute(self):
        '''
        Execute the step, checking that the precondition and postcondition are
        satisfied. Wrap functions so that they return the expected exception
        types.
        '''
        print_indented(
            0, '- Executing step {}:'.format(colored(self.name, 'yellow')),
            newline=False
        )

        # Check and store the initial state.
        initial = self.check_initial()
        self.initial = initial

        print_indented(1, 'Precondition:  ', newline=False, end='')

        # Check the precondition.
        if self.precondition(initial):
            print_indented(0, colored('SUCCESS', 'green'), newline=False)
        else:
            print_indented(0, colored('FAILURE', 'red'), newline=False)
            raise(
                PreconditionError(self.name, initial)
            )

        # Execute the action.
        self.action()

        # Check the postcondition.
        final = self.check_final()

        print_indented(1, 'Postcondition: ', newline=False, end='')

        if final == self.expected:
            print_indented(0, colored('SUCCESS', 'green'), newline=False)
        else:
            print_indented(0, colored('FAILURE', 'red'), newline=False)
            raise(
                PostconditionError(self.name, final, self.expected)
            )

    def rollback(self):
        '''
        Rollback the step and check that the resulting state is the one that
        was expected, that is, the initial state.
        '''
        # Execute the rollback.
        self.rollback_action()

        # Check the rollback postcondition.
        final = self.check_rollback()
        if not final == self.initial:
            raise(
                RollbackPostconditionError(self.name, final, self.initial)
            )

    # Helpers for the definition of steps.

    def set_stdout(self, stdout):
        '''
        Set the value of stdout for output of commands.
        '''
        self.stdout = stdout

    def check_call(self, args):
        '''
        The equivalent of 'check_call' from subprocess, but that uses the
        correct stout and stderr. Also prints the commands that is going to be
        executed.
        '''
        print_command(args, self.stdout)
        subprocess.check_call(
            args,
            stdout=self.stdout,
            stderr=subprocess.STDOUT,
        )

    def check_output(self, args):
        '''
        The equivalent of 'check_output' from subprocess, but that uses the
        correct stout and stderr. Also prints the commands that is going to be
        executed.
        '''
        print_command(args, self.stdout)
        return subprocess.check_output(
            args,
            stderr=self.stdout,
        )

    # Internal helpers

    def wrap(self, phase, action):
        '''
        Wrap an action so that it returns the appropriate exception. This also
        stores the exception so that it can be reported later.
        '''
        def wrapped_action():
            try:
                return action()
            except Exception:
                track = traceback.format_exc()
                raise(
                    ExecutionError(self.name, phase, track)
                )
        return wrapped_action

################################################################################
# Release

class Release:
    '''
    A complete release process. Execute the steps one by one, verifying that
    each of them are successful. If there is a failure, rollback automatically.

    Errors are reported at the end, explaining why there was a problem.
    '''

    def __init__(self, name, steps, stdout=None):
        self.name = name
        self.steps = steps

        self.executed_steps = []
        self.exceptions = []

        if stdout is None:
            self.stdout = StringIO()
            self.stdout_variable = True
        else:
            self.stdout = stdout
            self.stdout_variable = False

    def execute(self):
        '''
        Execute the release process and rollbacks if necessary.
        '''
        for step in self.steps:
            step.set_stdout(self.stdout)
            print_step(step.name, self.stdout)
            try:
                step.execute()
                self.executed_steps.append(step)

            except PreconditionError as exception:
                self.exceptions.append(exception)
                self.rollback()
                raise exception

            except PostconditionError as exception:
                self.exceptions.append(exception)
                self.executed_steps.append(step)
                self.rollback()
                raise exception

            except ExecutionError as exception:
                self.exceptions.append(exception)
                if exception.phase == Phase.CHECK_FINAL:
                    self.executed_steps.append(step)
                self.rollback()

                raise exception

        if self.stdout_variable:
            out = self.stdout.getvalue()
            message = '\n'.join([
                '<',
                '| Log from stdout and stderr:',
                '>',
                ])
            print(message)
            print(out)

    def rollback(self):
        '''
        Rollback the steps of the release that have been executed. Should not
        be called manually.
        '''
        for step in self.executed_steps:
            try:
                step.rollback()

            except Exception:
                break

        self.explain_exceptions()

    def explain_exceptions(self):
        '''
        Explain the exceptions that occurred during the release process.
        '''
        if self.exceptions:
            print_indented(
                0, 'The following errors ocurred during the release process.'
            )
            self.exceptions.reverse()
            for exception in self.exceptions:
                exception.explain()

################################################################################
# Phases

class Phase(Enum):
    '''
    Phases that can have exceptions due to side-effects.
    '''
    CHECK_INITIAL = auto()
    CHECK_FINAL = auto()
    CHECK_ROLLBACK = auto()
    EXECUTE = auto()
    ROLLBACK = auto()

################################################################################
# Exceptions

class ExecutionError(Exception):
    '''
    A wrapper for an execution error, showing from which part of the process
    the error comes from.

    This is supposed to wrap errors coming from side effects, and not logic
    errors.
    '''
    def __init__(self, name, phase, track):
        self.name = name
        self.phase = phase
        self.track = track
        super().__init__()

    def explain(self):
        '''
        Explain the execution error, including the traceback.
        '''
        explain_step(self.name)
        print_indented(
            1, 'Execution error during the "{}" phase:'.format(self.phase.name)
        )
        print_indented(1, self.track)

class PreconditionError(Exception):
    '''
    A precondition error.
    '''
    def __init__(self, name, state):
        self.name = name
        self.state = state
        super().__init__()

    def explain(self):
        '''
        Explain the precondition error.
        '''
        explain_step(self.name)
        print_indented(1, 'Precondition error, the observed state was:')
        print_indented(1, self.state)

class PostconditionError(Exception):
    '''
    A postcondition error.
    '''
    def __init__(self, name, actual_state, expected_state):
        self.name = name
        self.actual_state = actual_state
        self.expected_state = expected_state
        super().__init__()

    def explain(self):
        '''
        Explain the postcondition error.
        '''
        explain_step(self.name)
        print_indented(1, 'Postcondition error, the observed state was:')
        print_indented(1, self.actual_state)
        print_indented(1, 'while the expected state was:')
        print_indented(1, self.expected_state)

class RollbackPostconditionError(Exception):
    '''
    A rollback postcondition error.
    '''
    def __init__(self, name, actual_state, expected_state):
        self.name = name
        self.actual_state = actual_state
        self.expected_state = expected_state
        super().__init__()

    def explain(self):
        '''
        Explain the postcondition error.
        '''
        explain_step(self.name)
        print_indented(1, 'Rollback postcondition error, the observed state was:')
        print_indented(1, self.actual_state)
        print_indented(1, 'while the expected state was:')
        print_indented(1, self.expected_state)

def explain_step(step_name):
    '''
    Explain on which step the exception ocurred.
    '''
    msg = '- Error ocurred during step {}.'.format(colored(step_name, 'yellow'))
    print_indented(0, msg)

################################################################################
# Helpers

def print_indented(level, msg, newline=True, end='\n'):
    '''
    Print a message with a given identation level.
    '''
    if level == 0:
        print(msg, end=end, flush=True)
    else:
        print(' ' * 2 * level, msg, end=end, flush=True)

    if newline:
        print('')

def print_command(args, stdout):
    '''
    Print the command that is going to be executed.
    '''
    command = subprocess.list2cmdline(args)
    message = '\n'.join([
        '<',
        '| The following command is going to be executed:',
        '|',
        '| {}',
        '|',
        '>',
        ]).format(command)
    stdout.write(message)

def print_step(name, stdout):
    '''
    Print the step that is going to be executed.
    '''
    message = '\n'.join([
        '<',
        '| Executing step {}.',
        '>',
        ]).format(name)
    stdout.write(message)
