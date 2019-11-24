'''
Release steps for filesystem manipulation.
'''

import os
import os.path
import shutil
import tempfile
import release

class Copy(release.Step):
    '''
    Copy a file between two locations. The destination must not exist.
    '''

    def __init__(self, src_path, dest_path):

        def check():
            return {
                'destination_exists': os.path.exists(dest_path)
            }

        def action():
            with tempfile.TemporaryDirectory() as dir_path:
                tmp_path = os.path.join(dir_path, 'temporary')
                shutil.copyfile(src_path, tmp_path)
                shutil.move(tmp_path, dest_path)

        def rollback_action():
            os.remove(dest_path)

        super().__init__(
            name='copy {} to {}'.format(src_path, dest_path),
            check=check,
            precondition=lambda s: not s['destination_exists'],
            expected={'destination_exists': True},
            action=action,
            rollback_action=rollback_action,
        )

class Symlink(release.Step):
    '''
    Create a symbolic link to a file. The destination must not exist.
    '''

    def __init__(self, src_path, link_path):

        def check():
            file_exists = False
            link = None
            if os.path.exists(link_path):
                file_exists = True
                if os.path.islink(link_path):
                    link = os.readlink(link_path)
            return {
                'file_exists': file_exists,
                'link': link,
            }

        def precondition(state):
            return not state['file_exists']

        def action():
            os.symlink(src_path, link_path)

        def rollback_action():
            os.remove(link_path)

        super().__init__(
            name='link {} to {}'.format(link_path, src_path),
            check=check,
            precondition=precondition,
            expected={'file_exists': True, 'link': src_path},
            action=action,
            rollback_action=rollback_action,
        )

class Unlink(release.Step):
    '''
    Remove a symbolic link to a file. The link must exist.
    '''

    def __init__(self, link_path):

        def check():
            file_exists = False
            link = None
            if os.path.exists(link_path):
                file_exists = True
                if os.path.islink(link_path):
                    link = os.readlink(link_path)
            return {
                'file_exists': file_exists,
                'link': link,
            }

        def precondition(state):
            pred1 = not state['file_exists']
            pred2 = state['link'] is not None
            return pred1 or pred2

        def action():
            if self.initial['file_exists']:
                os.remove(link_path)

        def rollback_action():
            if self.initial['file_exists']:
                os.symlink(self.initial['link'], link_path)

        super().__init__(
            name='unlink {}'.format(link_path),
            check=check,
            precondition=precondition,
            expected={'file_exists': False, 'link': None},
            action=action,
            rollback_action=rollback_action,
        )
