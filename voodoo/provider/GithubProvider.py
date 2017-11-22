from .BaseProvider import BaseProvider

__all__ = ['GithubProvider']


class GithubProvider(BaseProvider):
    """
    Github Releases
    """

    # optional = ('tag')
    required_attributes = ('user', 'repo')
    typ = 'github'

