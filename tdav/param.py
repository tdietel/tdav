
import yaml
from pathlib import Path
from pprint import pprint

class param:

    def __init__(self):

        self.profiles = {}
        self.default_profile = None
        self.current_profile = None

        self.upscripts = []

        try:
            self.read_config( Path.home() / ".tdav.yaml" )

        except FileNotFoundError as ex:
            print("Configuration file \"~/.tdav.yaml\"} not found - skipping")
            pass


    def read_config(self, cfgfile):

        with open( cfgfile ) as f:
            cf = yaml.safe_load(f)

        # pprint(cf)

        if 'profiles' in cf:
            self.profiles.update(cf['profiles'])

        if 'default_profile' in cf:
            if cf['default_profile']=="" or cf['default_profile']==False:
                self.default_profile = None
            else:
                self.default_profile = cf['default_profile']

        if 'upload_scripts' in cf:
            self.upscripts += cf['upload_scripts']
