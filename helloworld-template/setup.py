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
setup(name='helloworld',
      sdk_version='0.2.0',
      version='0.0.0',
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
      linkedge = Application:main
      """)
