#coding:utf-8
'''
Created on 2013-6-15
运行sudo python setup.py install 来安装dnspod-data依赖
@author: samchi
'''
from distutils.core import setup

setup(name='shard.py',
      version='0.0.1',
      description=u'哎哟数据访问工具',
      author='Sam Chi',
      author_email='hzchi@dnspod.com',
      url='http://scm.office.weisuo.net/hzchi/dnspod-data',
      packages=['shardpy'],
      long_description=u'哎哟数据访问工具, 支持ORM、散表、读写分离等等',
      license="Public domain",
      platforms=["any"],
     )