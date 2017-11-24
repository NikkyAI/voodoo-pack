from .BaseProvider import BaseProvider

__all__ = ['GithubProvider']


class GithubProvider(BaseProvider):
    """
    Github Releases
    """

    # optional = ('tag')
    _required_attributes = ('user', 'repo')
    _typ = 'github'

