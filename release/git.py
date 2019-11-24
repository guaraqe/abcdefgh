'''
Release steps for manipulating Git repositories.
'''

import release

class Fetch(release.Step):
    '''
    Fetch a remote to git repository in a given path.
    '''
    def __init__(self, path, remote='origin'):

        def action():
            self.check_call([
                'git',
                '--git-dir', path,
                'fetch', remote,
            ])

        super().__init__(
            name='git fetch {} at {}'.format(remote, path),
            check=lambda: {},
            precondition=lambda _: True,
            expected={},
            action=action,
            rollback_action=lambda: None,
        )
