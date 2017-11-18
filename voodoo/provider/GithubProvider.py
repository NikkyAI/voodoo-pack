from .BaseProvider import *
__all__ = ['GithubProvider']
class GithubProvider(BaseProvider):
    
    optional = ('tag')
    required = ('user', 'repo')
    typ = 'github'

    def __init__(self):
        super()
        print("GithubProvider .ctor")
    