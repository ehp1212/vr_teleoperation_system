from setuptools import find_packages, setup

package_name = 'teleop_bridge'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        "setuptools", 
        "ultralytics>=8.0.0",
        "opencv-python",
        ],
    zip_safe=True,
    maintainer='eun',
    maintainer_email='eunhyeon1212p@gmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'bridge_node = teleop_bridge.main:main',
        ],
    },
)
