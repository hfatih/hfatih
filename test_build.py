import copy
import json
import unittest
from unittest.mock import patch

import build


def page(name, has_next, cursor):
    return {'data': {'user': {
        'name': 'Fatih HAN',
        'repositories': {
            'nodes': [{'name': name, 'releases': {'totalCount': 0}}] if name else [],
            'pageInfo': {'hasNextPage': has_next, 'endCursor': cursor},
        },
    }}}


class FetchTests(unittest.TestCase):
    def test_all_repository_pages_are_kept_for_both_auth_paths(self):
        for token in ('', 'test-token'):
            with self.subTest(token=bool(token)):
                pages = [page('first', True, 'cursor-1'), page('second', True, 'cursor-2'), page('last', False, 'cursor-3')]
                variables = []

                def reply(payload):
                    variables.append(payload['variables'])
                    return copy.deepcopy(pages[len(variables) - 1])

                def send(request):
                    return reply(json.loads(request.data))

                def cli(args, **kwargs):
                    payload = json.loads(kwargs['input']) if 'input' in kwargs else {'variables': {'cursor': None, 'since': args[-1].split('=', 1)[1]}}
                    return unittest.mock.Mock(stdout=json.dumps(reply(payload)))

                def api(path, *args):
                    return {'open_issues_count': 0} if '?' not in path else []

                with patch.dict(build.os.environ, {'GITHUB_TOKEN': token}), patch.object(build, 'send', side_effect=send), patch.object(build.subprocess, 'run', side_effect=cli), patch.object(build, 'api', side_effect=api):
                    user = build.fetch()

                self.assertEqual([repo['name'] for repo in user['repositories']['nodes']], ['first', 'second', 'last'])
                self.assertEqual([item['cursor'] for item in variables], [None, 'cursor-1', 'cursor-2'])
                self.assertEqual(len({item['since'] for item in variables}), 1)

    def test_error_on_later_page_stops_instead_of_drawing_partial_data(self):
        with patch.dict(build.os.environ, {'GITHUB_TOKEN': 'test-token'}), patch.object(build, 'send', side_effect=[page('first', True, 'cursor-1'), {'errors': [{'message': 'query failed'}]}]), patch.object(build, 'api', side_effect=lambda path, *args: {'open_issues_count': 0} if '?' not in path else []) as api:
            with self.assertRaisesRegex(SystemExit, 'query failed'):
                build.fetch()
            api.assert_not_called()

    def test_empty_repository_page(self):
        with patch.dict(build.os.environ, {'GITHUB_TOKEN': 'test-token'}), patch.object(build, 'send', return_value=page(None, False, None)):
            self.assertEqual(build.fetch()['repositories']['nodes'], [])


if __name__ == '__main__':
    unittest.main()
