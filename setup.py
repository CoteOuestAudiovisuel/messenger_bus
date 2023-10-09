from setuptools import setup, find_packages

setup(

    name='messenger_bus',
    version='1.0.11',
    description='Bus messaging system',
    url='https://github.com/CoteOuestAudiovisuel/messenger_bus',
    author='Zacharie Assagou',
    author_email='zacharie.assagou@coteouest.ci',
    license='BSD 2-clause',
    packages=['messenger_bus'],
    install_requires=['pika','pyyaml','jsonschema'],
    include_package_data=True,
    classifiers=[],

)