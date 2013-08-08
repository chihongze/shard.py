# 关于shard.py
shard.py 是在web.py数据库访问模块的基础上增加了读写分离、shard以及ORM的功能
# 基本配置
shard.py需要两个配置文件，一个是连接池配置文件，一个是节点配置文件，配置文件的位置由web.config.dbpool和web.config.dbnodes来指定
## 连接池配置
shard.py支持多个连接池策略，这些策略统一存放在连接池配置中，因为使用的是DBUtils的PooledDB连接池，所有配置项是与PooledDB相同的
<pre>
[default]
mincached = 10
maxcached = 20
maxshared = 0
maxconnections = 0
blocking = 1
maxusage = 0
</pre>
需要注意的是必须要指定一个名为defaul的策略
## 节点配置
节点配置文件用来配置MySQL服务节点,由多行json组成
<pre>
{"name":"user", "write":"true", "read":"true", "host":"172.4.2.1", "user":"test", "pw":"ailuntan", "db":"ailuntan-center", "pool_policy":"default"}
{"name":"user", "write":"false", "host":"172.4.2.2", "user":"test", "pw":"ailuntan", "db":"ailuntan-center", "pool_policy":"default"}
</pre>
* name: 业务名称
* write: 该数据源是否是可写的
* read: 如果数据源可写，那么该数据源是否可读
* host: 主机地址
* user: 用户名
* pw: 密码
* db: 数据库名称
* pool_policy:使用的连接池策略,使用default可以不写此项
# 基本使用
运行sudo python ./setup.py install 之后
<pre>
import web
web.config.dbnodes = '/data/ailuntan/conf/dbnodes.conf'
web.config.dbpool = '/data/ailuntan/conf/dbpool.conf'

from shardpy import db
</pre>
就可以使用shardpy了!
## 读取数据
### 从db中获取一个对象
user = db.user.query_one(clazz=User, table='users', where='id=$id', vars={'id':283})
* clazz:要映射的model类
* table:使用的表名,可以不指定，会根据clazz的名称自己生成表名，比如User->user UserDetails->user_details
* where、vars这些的使用同web.py的db模块
其中user就是节点配置中的name，这里会根据操作自动选择是用读的数据源和写的数据源，多个读的数据源会随机选择一个，返回结果会自动进行orm
### 从db中获取对象列表
user_list = db.user.query_list(clazz=User, table='users', offset=0, limit=10)
### 从db中获取某个字段的值
user_count = db.query_one_field(table='users', what='count(1) as c', field='c')
### 从db中获取某个字段的一系列值
email_list = db.query_field_list(table='users', what='email', field='email', limit=10)
## 插入数据
### 普通插入
<pre>
std = Student()
std.name, std.age, std.score = 'Sam', 23, 100
print '>>>> gen Id:', db.test.insert(model=std)
</pre>
支持插入一个对象，如果表名与model的类名不能匹配，比如model类名为User,而表名为users，那么需要用table参数显式的指定表名，另外如果有些字段不希望插入，那么可以指定without参数来过滤，比如db.test.insert(model=std, without=('id',))
model的类型可以是普通的对象，也可以是dict,如果使用dict那么必须使用table去显式的指定一个表名
### 批量插入
<pre>
records = []
records.append({'name':'Sam', 'age':23, 'score':100})
records.append({'name':'Jack', 'age':25, 'score':90})
records.append({'name':'Nick', 'age':30, 'score':50})
db.test.multi_insert('student', records)
</pre>
## 更新数据
支持根据python对象来更新记录,比如给用户改姓名：
student.name = u'迟宏泽'
db.test.update(model=student, keys=('id',), field_name=('name',))
* model: 要更新的对象
* keys: 根据哪些属性值进行更新，就是where条件，默认是'id'
* field_name: 要更新的字段，如果不填写，那么整个对象的字段都会更新
## 删除数据
同web.py的操作:
db.test.delete(table='student', where='name=$name', vars={'name':'Sam'})
# Shard
shardpy最大的特色就是可以像普通数据库操作一样操作被shard的DB
## shard节点的配置
<pre>
{"name":"comment", "write":"true", "read":"true", "host":"172.4.2.2", "user":"test", "pw":"ailuntan", "db":"aiyou-data_01", "pool_policy":"default", "shard_begin":0, "shard_end":499}
</pre>
<pre>
{"name":"comment", "write":"true", "read":"true", "host":"172.4.2.3", "user":"test", "pw":"ailuntan", "db":"aiyou-data_01", "pool_policy":"default", "shard_begin":500, "shard_end":999}
</pre>
只需要较常规配置多增加两个配置项：
* shard_begin:shard起始段
* shard_end:shard结束段
## 数据访问
同普通的数据访问，只不过需要增加一个shard值：
<pre>
  comment = db.comment.query_one(clazz=Comment,
                         where='user_id=$user_id', vars={'user_id':1000}, shard=1000)
</pre>
这里指定的shard值是1000, 那么shardpy会自动做取模计算1000 % (999+1), 得到hash值为0,那么就会找到172.4.2.2的comment数据源，并自动替换表名，comment->comment_0000 (默认的shard表名规则), 如果你的表名规则不同，那么需要一个额外的tablename_formatter参数，这个参数指向一个计算表名的函数回调。
