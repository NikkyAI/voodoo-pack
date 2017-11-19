from .BaseProvider import *
__all__ = ['JenkinsProvider']
class JenkinsProvider(BaseProvider):
    
    optional = ('tag')
    required = ('user', 'repo')
    typ = 'github'

    def __init__(self):
        super()
        print("JenkinsProvider .ctor")
    
    # http://YOUR_JENKINS:8080/job/YOUR_JOB/api/