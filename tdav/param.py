
import yaml
from pathlib import Path
from pprint import pprint

class param:

    def __init__(self):

        self.connect = None
        self.profiles = {}
        self.default_profile = None
        self.current_profile = None

        self.upscripts = []
        self.filepatterns = []

        self.verbosity = 1

        for cfgfile in ( Path.home() / ".tdav.yaml", Path("tdav.yaml") ):
            if cfgfile.exists():
                print(f"Reading {cfgfile}")
                self.read_config( cfgfile )

    def read_config(self, cfgfile):

        with open( cfgfile ) as f:
            cf = yaml.safe_load(f)


        if 'profiles' in cf:
            self.profiles.update(cf['profiles'])

        if 'default_profile' in cf:
            if cf['default_profile']=="" or cf['default_profile']==False:
                self.default_profile = None
            else:
                self.default_profile = cf['default_profile']

        if 'upload_scripts' in cf:
            self.upscripts += cf['upload_scripts']

        if 'filepatterns' in cf:
            self.filepatterns += cf['filepatterns']

        if 'connect' in cf:
            self.connect = cf['connect']

        if 'verbosity' in cf:
            self.verbosity = cf['verbosity']
