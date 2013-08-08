'''
Created on 2013-8-8
shard test case
@author: samchi
'''
import web
web.config.dbnodes = '/data/ailuntan/conf/dbnodes.conf'
web.config.dbpool = '/data/ailuntan/conf/dbpool.conf'

from shardpy import db
import datetime
import unittest

class Comment(object):
    
    def __str__(self):
        return str(self.__dict__)

class Test(unittest.TestCase):


#    def testInsert(self):
#        comment = Comment()
#        comment.object_id, comment.user_id = 100000, 1000
#        comment.updated, comment.body = datetime.datetime.now(), 'Hello, world!'
#        db.comment.insert(model=comment,shard=comment.user_id)
        
    def testQueryOne(self):
        comment = db.comment.query_one(clazz=Comment,
                         where='user_id=$user_id', vars={'user_id':1000}, shard=1000)
        print ">>>>>>> Comment:", comment
        
    def testQueryList(self):
        comments = db.comment.query_list(clazz=Comment, 
                        where='user_id=$user_id', vars={'user_id':1000}, shard=1000)
        print ">>>>>>>>>>> Comments <<<<<<<<<<<<<<<"
        for comment in comments:
            print comment
            
    def testDelete(self):
        db.comment.delete(table='comment', where='user_id=$user_id', vars={'user_id':1000}, shard=1000)


if __name__ == "__main__":
    unittest.main()