from .BaseProvider import *
__all__ = ['MavenProvider']
class MavenProvider(BaseProvider):
    
    optional = ()
    required = ('remoteRepository', 'group', 'artifact', 'version')
    typ = 'mvn'

    def __init__(self):
        super()
        print("MavenProvider .ctor")

    