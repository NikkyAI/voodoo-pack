import hashlib
import os
from mvn.requestor import Requestor, RequestException
from maven.resolver import Resolver
from maven.artifact import Artifact
import sys
import getopt
import requests

class Downloader(object):
    def __init__(self, base="http://repo1.maven.org/maven2", username=None, password=None):
        self.requestor = Requestor(username, password)
        self.resolver = Resolver(base, self.requestor)



    def download(self, artifact, filename=None, suppress_log=False):
        filename = artifact.get_filename(filename)
        url = self.resolver.uri_for_artifact(artifact)

        if not self.verify_md5(filename, url + ".md5"):
            if not suppress_log:
                print("Downloading artifact " + str(artifact))

            onError = lambda uri, err: print("Failed to download artifact " + str(artifact) + "from " + uri, file=sys.stderr)
            response = self.requestor.request(url, onError, lambda r: r)

            if response:

                with open(filename, 'wb') as f:
                    f.write(response.content)
                if not suppress_log:
                    print("Downloaded artifact %s to %s" % (artifact, filename))
                return (artifact, True)
            else:
                return (artifact, False)
        else:
            if not suppress_log:
                print("%s is already up to date" % artifact)
            return (artifact, True)

    def verify_md5(self, file, remote_md5):
        if not os.path.exists(file):
            return False
        else:
            local_md5 = self._local_md5(file)
            onError = lambda uri, err: print("Failed to download MD5 from " + uri, file=sys.stderr)
            remote = self.requestor.request(remote_md5, onError, lambda r: str(r.text))
            return local_md5 == remote

    def _local_md5(self, file):
        md5 = hashlib.md5(open(file, 'rb').read())
        return md5.hexdigest()


__doc__ = """
   Usage:
   %(program_name)s <options> Maven-Coordinate filename
   Options:
     -m <url>      --maven-repo=<url>
     -u <username> --username=<username>
     -p <password> --password=<password>

   Maven-Coordinate are defined by: http://maven.apache.org/pom.html#Maven_Coordinates
      The possible options are:
      - groupId:artifactId:version
      - groupId:artifactId:packaging:version
      - groupId:artifactId:packaging:classifier:version
    filename is optional. If not supplied the filename will be <artifactId>.<extension>
    The filename directory must exist prior to download.

   Example:
     %(program_name)s "org.apache.solr:solr:war:3.5.0"
  """

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "m:u:p:", ["maven-repo=", "username=", "password="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print(str(err)) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    if not len(args):
        print("No maven coordiantes supplied")
        usage()
        sys.exit(2)
    else:
        options = dict(opts)
        base = options.get("-m")
        if not base:
            base = options.get("--maven-repo")
        if not base:
            base = "https://repo1.maven.org/maven2"
        username = options.get("-u")
        if not username:
            username = options.get("--username")
        password = options.get("-p")
        if not password:
            options.get("--password")
        dl = Downloader(base, username, password)

        artifact = Artifact.parse(args[0])

        filename = None
        if len(args) == 2:
            filename = args[1]
        try:

            if dl.download(artifact, filename):
                sys.exit(0)
            else:
                usage()
                sys.exit(1)
        except RequestException as e:
            print(e.msg)
            sys.exit(1)


def usage():
    print(__doc__ % {'program_name': os.path.basename(sys.argv[0])})

if __name__ == '__main__':
    main()
