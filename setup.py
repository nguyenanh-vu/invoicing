import sys
from setuptools import setup

sys.path.append("./src")
import __version__

version = __version__.__version__

setup(
   name='invoicing',
   version=version,
   description='Module for automating invoicing creation',
   license="GPLv3",
   long_description="",
   author='nguyenanh-vu',
   author_email='nguyenanhvu08@gmail.com',
   url="https://github.com/nguyenanh-vu/invoicing",
   packages=['invoicing'],
   package_dir = {'invoicing': 'src'},
   #data_files = [('config', ['data/conf/conf.ini.template'])],
   entry_points={
        'console_scripts': [
            'invoicing = invoicing:cli',
        ]
   },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities"
    ],
   install_requires=["google-auth-oauthlib",
                     "google-auth-httplib2",
                     "google-api-python-client"
                     ]
)