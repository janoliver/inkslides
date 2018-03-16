from setuptools import setup

setup(
    name='inkslides',
    version='2.1.0',

    setup_requires=['lxml'],

    description='Generate PDF presentations with inkscape',

    url='https://github.com/janoliver/inkslides',
    author='Jan Oliver Oelerich',

    license='License :: OSI Approved :: MIT License',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'License :: OSI Approved :: MIT License'
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],

    packages=['inkslides'],
    entry_points={
        'console_scripts': [
            'inkslides = inkslides.inkslides:main',
        ],
    },
)
