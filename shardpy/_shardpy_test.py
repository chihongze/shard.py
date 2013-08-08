#coding:utf-8
'''
Created on 2013-8-7
测试用例
@author: samchi
'''

import web
web.config.dbnodes = '/data/ailuntan/conf/dbnodes.conf'
web.config.dbpool = '/data/ailuntan/conf/dbpool.conf'

from shardpy import db
import unittest

class User(object):
    
    def __str__(self):
        return str(self.__dict__)
    
class Student(object):
    
    def __str__(self):
        return str(self.__dict__)

class Test(unittest.TestCase):
    
    def testBasicQueryOne(self):
        user = db.user.query_one(clazz=User, table='users', where='id=$id', vars={'id':283})
        print user
    
    def testBasicQueryList(self):
        user_list = db.user.query_list(clazz=User, table='users', offset=0, limit=10)
        for user in user_list:
            print '>>> user:', user
    
    def testInsert(self):
        std = Student()
        std.name, std.age, std.score = 'Sam', 23, 100
        print '>>>> gen Id:', db.test.insert(model=std)
    
    def testMultiInsert(self):
        records = []
        records.append({'name':'Sam', 'age':23, 'score':100})
        records.append({'name':'Jack', 'age':25, 'score':90})
        records.append({'name':'Nick', 'age':30, 'score':50})
        db.test.multi_insert('student', records)
        
    def testDelete(self):
        db.test.delete(table='student', where='name=$name', vars={'name':'Sam'})
        
    def testUpdate(self):
        student = db.test.query_one(clazz=Student, where='id=$id', vars={'id':5})
        student.name = u'迟宏泽'
        db.test.update(model=student)
        
    def testQuery(self):
        csr = db.test.query(sql='select name from student')
        print '>>>>>>>> Test Free Query <<<<<<<<<<<'
        for row in csr:
            print "----> name:", row['name']
            
    def testQueryOneField(self):
        print '>>>>>> Count:', db.test.query_one_field(what='count(1) as c',
                    table='student', field='c')
    
    def testQueryFieldList(self):
        print '>>>>>>> Name List:'
        name_list = db.test.query_field_list(what='name', table='student')
        for name in name_list:
            print ">>>>>> Name:", name

if __name__ == "__main__":
    unittest.main()