# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PyQt5 import QtCore


class RepositoryMonitor(QtCore.QObject):
    """
    This class can be used to listen for changes in the saved repository list.
    """
    sgnUpdated = QtCore.pyqtSignal()
    _instance = None

    def __new__(cls):
        """
        Implements the singleton pattern.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


K_REPO_MONITOR = RepositoryMonitor()


class Repository:
    """
    A repository of metastat as a RESTful API endpoint.
    """

    def __init__(self, name: str, uri: str):
        """Initialize the repository instance."""
        self._name = name
        self._uri = uri
        # TODO: Authentication will be added later

    @property
    def name(self):
        """Returns the repository name."""
        return self._name

    @property
    def uri(self):
        """Returns the repository uri."""
        return self._uri

    #############################################
    # INTERFACE
    #################################

    @classmethod
    def load(cls) -> list[Repository]:
        """Load the repositories list from user preferences."""
        repos = []  # type: list[Repository]
        settings = QtCore.QSettings()
        for index in range(settings.beginReadArray('metastat/repositories')):
            settings.setArrayIndex(index)
            repos.append(Repository(
                name=settings.value('name'),
                uri=settings.value('uri'),
            ))
        return repos

    @classmethod
    def save(cls, repositories: list[Repository]) -> None:
        """Save the repository in the user preferences."""
        settings = QtCore.QSettings()
        settings.beginWriteArray('metastat/repositories')
        for index, repo in enumerate(repositories):
            settings.setArrayIndex(index)
            settings.setValue('name', repo.name)
            settings.setValue('uri', repo.uri)
        settings.endArray()
        K_REPO_MONITOR.sgnUpdated.emit()
