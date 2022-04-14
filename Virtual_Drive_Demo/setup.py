'''
name: APP名称，
sdk_version: python SDK版本
version: APP版本
packages： APP源代码路径
package_dir： APP源代码路径
install_requires： 安装依赖
entry_points： 程序执行的入口
'''
from setuptools import setup, find_packages
setup(name='Virtual_Drive_Demo',
      version='1.0.0',
      sdk_version='1.4.5',
      author='Inhand',
      author_email='',
      description='',
      license='PRIVATE',
      packages=find_packages('src'),
      package_dir={'': 'src'},
      zip_safe=False,
      install_requires=[],
      entry_points="""
      [console_scripts]
      appname = Application:main
      """)
