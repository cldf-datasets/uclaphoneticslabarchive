from setuptools import setup


setup(
    name='cldfbench_uclaphoneticslabarchive',
    py_modules=['cldfbench_uclaphoneticslabarchive'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'uclaphoneticslabarchive=cldfbench_uclaphoneticslabarchive:Dataset',
        ],
        'cldfbench.commands': [
            'ucla=ucla_commands',
        ]
    },
    install_requires=[
        'cldfbench',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
