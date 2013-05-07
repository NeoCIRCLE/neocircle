from setuptools import setup, find_packages
setup(
    name = "CloudGUI",
    version = "0.3",
    data_files = [('/usr/share/icons', ['cloud.svg']),
                    ('/usr/share/applications', ['cloud.desktop'])],
    include_package_data = True,
    packages = ['cloudgui',], 
    scripts = ['cloud','rdp',],
    )
