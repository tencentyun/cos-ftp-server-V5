from setuptools import setup, find_packages

from ftp_v5.version import version


def requirements():
    with open('requirements', 'rt') as fin:
        requirements = [line.strip() for line in fin]
        return requirements


print find_packages()

setup(
    name='cos-ftp-server-v5',
    version=version,
    author='COS team',
    author_email='iainyu@tencent.com',
    maintainer='iainyu',
    maintainer_email='iainyu@tencent.com',
    url='https://cloud.tencent.com/product/cos',
    license='MIT',
    description='The ftp gateway for cos service,supporting the multi bucket.',
    packages=find_packages(),
    install_requires=requirements(),
    include_package_data=True
)
