# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))


setup(
    name='zbuspy', 
    version='0.8.4', 
    description='zbus python client', 

    # The project's main homepage.
    url='https://gitee.com/rushmore/zbus-python',

    # Author details
    author='Rushmore (Leiming Hong)',
    author_email='hong.leiming@qq.com',

    # Choose your license
    license='MIT',
 
    classifiers=[  
        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
 
    keywords='MQ RPC ServiceBus SOA', 
    packages=['zbus'],
)