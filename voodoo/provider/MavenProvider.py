from .BaseProvider import BaseProvider

__all__ = ['MavenProvider']


class MavenProvider(BaseProvider):

    # optional = ()
    required_attributes = ('remoteRepository', 'group', 'artifact', 'version')
    typ = 'mvn'
