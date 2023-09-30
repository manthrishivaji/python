import sys
from abc import ABC, abstractmethod
from datetime import datetime

import requests

from database import DatabaseManager

db = DatabaseManager('bookmarks.db')


class Command(ABC):
    @abstractmethod
    def execute(self, data):
        raise NotImplementedError('Commands must implement an execute method')


class CreateBookmarksTableCommand(Command):
    def execute(self, data=None):
        db.create_table('bookmarks', {
            'id': 'integer primary key autoincrement',
            'title': 'text not null',
            'url': 'text not null',
            'notes': 'text',
            'date_added': 'text not null',
        })


class AddBookmarkCommand(Command):
    def execute(self, data, timestamp=None):
        data['date_added'] = timestamp or datetime.utcnow().isoformat()
        db.add('bookmarks', data)
        return 'Bookmark added!'


class ListBookmarksCommand(Command):
    def __init__(self, order_by='date_added'):
        self.order_by = order_by

    def execute(self, data=None):
        return db.select('bookmarks', order_by=self.order_by).fetchall()


class DeleteBookmarkCommand(Command):
    def execute(self, data):
        db.delete('bookmarks', {'id': data})
        return 'Bookmark deleted!'


class QuitCommand(Command):
    def execute(self, data=None):
        sys.exit()


class ImportGitHubStarsCommand(Command):
    def _extract_bookmark_info(self, repo):
        return {
            'title': repo['name'],
            'url': repo['html_url'],
            'notes': repo['description'],
        }

    def execute(self, data):
        bookmarks_imported = 0

        github_username = data['github_username']
        next_page_of_results = f'https://api.github.com/users/{github_username}/starred'

        while next_page_of_results:  # <1>
            stars_response = requests.get(
                next_page_of_results,
                headers={'Accept': 'application/vnd.github.v3.star+json'},
            )
            next_page_of_results = stars_response.links.get('next', {}).get('url')

            for repo_info in stars_response.json():  # <2>
                repo = repo_info['repo']

                if data['preserve_timestamps']:  # <3>
                    timestamp = datetime.strptime(
                        repo_info['starred_at'],
                        '%Y-%m-%dT%H:%M:%SZ'
                    )
                else:  # <4>
                    timestamp = None

                bookmarks_imported += 1
                AddBookmarkCommand().execute(
                    self._extract_bookmark_info(repo),
                    timestamp=timestamp,
                )  # <5>

        return f'Imported {bookmarks_imported} bookmarks from starred repos!'


class EditBookmarkCommand(Command):
    def execute(self, data):
        db.update(
            'bookmarks',
            {'id': data['id']},
            data['update'],
        )
        return 'Bookmark updated!'
