from setuptools import setup, find_packages


def requirements():
    with open('requirements','rt') as fin:
        requirements = [line.strip() for line in fin]
        return requirements

setup(
    name='cos-ftp-server-v5',
    version='0.1.0',
    url='https://cloud.tencent.com/',
    license='MIT',
    author='COS team',
    author_email='iainyu@tencent.com',
    description='The ftp gateway for cos service',
    packages=find_packages(),
    install_requires=requirements(),
    include_package_data=True,
    entry_points={
        'console_scripts':[
            'cos_ftp_server=ftp_server:main'
        ],
    }
)