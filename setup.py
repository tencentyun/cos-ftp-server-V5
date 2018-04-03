from setuptools import setup, find_packages


def requirements():
    with open('requirements','rt') as fin:
        requirements = [line.strip() for line in fin]
        return requirements

setup(
    name='cos-ftp-server-v5',
    version='1.1.0',
    url='https://cloud.tencent.com/',
    license='MIT',
    author='COS team',
    author_email='iainyu@tencent.com',
    description='The ftp gateway for cos service， supporting the multi bucket.',
    packages=find_packages(),
    install_requires=requirements(),
    include_package_data=True
)