#coding:utf-8
'''
Created on 2013-8-7
数据库访问工具,读写分离、ORM和散表的处理
@author: samchi
'''
from ConfigParser import ConfigParser
from abc import ABCMeta, abstractmethod
from web.db import database
import json
import random
import re
import threading
import web

class ShardDBException(Exception):
    
    '''Sharddb模块自身错误所抛出的异常类型'''
    
    def __init__(self, message):
        self.message = message
    

_pool_cfg_file, _db_cfg_file = web.config.dbpool, web.config.dbnodes

# 加载连接池策略
def _load_pool_policy():
    
    cf = ConfigParser()
    cf.read(_pool_cfg_file)
    
    sections = cf.sections()
    if 'default' not in sections:
        raise ShardDBException(u'必须指定一个名称为default的连接池配置策略!')
    
    _pool_policy = {}
    for policy_name in sections:
        _pool_policy[policy_name] = {k:int(v) for k,v in cf.items(policy_name)}
    
    return _pool_policy

_pool_policy = _load_pool_policy()


# 配置保留字        
_config_fields = {'name', 'write', 'read', 'pool_policy', 'shard_begin', 'shard_end'}

_table_name_cache = {} # 缓存表名
_table_name_cache_lock = threading.Lock()
class _BaseDataAccessProxy(object):
    
    __metaclass__ = ABCMeta
    
    def gen_db(self, node_cfg):
        pool_policy = node_cfg.get('pool_policy', 'default')
        node_cfg['pooling'], node_cfg['dbn'] = True, 'mysql'
        node_cfg.update(_pool_policy[pool_policy])
        if 'port' in node_cfg:
            node_cfg['port'] = int(node_cfg['port'])
        else:
            node_cfg['port'] = 3306
        return database(**{k:v for k, v in node_cfg.items() if k not in _config_fields})
    
    def get_db_access(self, node):
        '''
        获取db节点的访问权限
        @return 0 是否可读
        @return 1 是否可写
        '''
        return node['write'] == 'false' or node['read'] == 'true', node['write'] == 'true'
    
    @abstractmethod
    def get_read_db(self, *args):pass
    
    @abstractmethod
    def get_write_db(self, *args):pass
    
    def __modelname2tablename(self, model_name):
        '将Model类名转换为表名,比如UserInfo->user_info'
        if model_name not in _table_name_cache:
            _table_name_cache_lock.acquire()
            if model_name not in _table_name_cache:
                table_name_buffer = []
                for index, char in enumerate(model_name):
                    if char.isupper():
                        if index != 0:table_name_buffer.append('_')
                        table_name_buffer.append(char.lower())
                    else:
                        table_name_buffer.append(char)
                table_name = ''.join(table_name_buffer)
                _table_name_cache[model_name] = table_name
            _table_name_cache_lock.release()
        return _table_name_cache[model_name]
    
    def gen_table_name(self, **kws):
        if 'table' in kws:
            return kws['table']
        if 'clazz' in kws:
            return self.__modelname2tablename(kws['clazz'].__name__)
        if 'model' in kws:
            return self.__modelname2tablename(kws['model'].__class__.__name__)
        raise ShardDBException(u'必须指定一个表名或者映射的类')
    
    def __map_row(self, row_data, clazz):
        model = clazz()
        model.__dict__.update(row_data)
        return model
    
    def __map_rows(self, csr, clazz):
        if csr:
            return [self.__map_row(row, clazz) for row in csr]
        else:
            return []
        
    def __map_one_row(self, csr, clazz):
        if csr:
            return self.__map_row(csr[0], clazz)
        else:
            return None
    
    def query_one(self, **kws):
        csr = self.get_read_db(**kws).select(tables=self.gen_table_name(**kws), 
                        what=kws.get('what', '*'), where=kws.get('where'), 
                        vars=kws.get('vars'), order=kws.get('order'), limit=1)
        return self.__map_one_row(csr, kws['clazz'])
    
    def query_list(self, **kws):
        csr = self.get_read_db(**kws).select(tables=self.gen_table_name(**kws),
                        what=kws.get('what', '*'), where=kws.get('where'), vars=kws.get('vars'), 
                        order=kws.get('order'), offset=kws.get('offset'), limit=kws.get('limit'))
        return self.__map_rows(csr, kws['clazz'])
    
    def query_one_field(self, **kws):
        csr = self.get_read_db(**kws).select(tables=self.gen_table_name(**kws),
                        what=kws['what'], where=kws.get('where'), vars=kws.get('vars'),
                        order=kws.get('order'), offset=None, limit=1)
        if not csr:return None
        field_name = kws['field'] if 'field' in kws else kws['what']
        return csr[0][field_name]
    
    def query_field_list(self, **kws):
        csr = self.get_read_db(**kws).select(tables=self.gen_table_name(**kws),
                        what=kws['what'], where=kws.get('where'), vars=kws.get('vars'),
                        order=kws.get('order'), offset=kws.get('offset'), limit=kws.get('limit'))
        if not csr:return []
        field_name = kws['field'] if 'field' in kws else kws['what']
        return [row[field_name] for row in csr]
    
    def insert(self, **kws):
        
        '''
        向DB中插入一个对象
        @param model 可以是对象也可以是字典
        @param table 表名, 如果model是字典的话那么table必须指定
        @param without 指定哪些字段不需要插入
        @return 返回插入对象的主键值
        '''
        
        model, table, without = kws.get('model'), kws.get('table'), kws.get('without', ('id',))
        
        fields = {}
        if isinstance(model, dict):
            fields = model
            if not table:raise ShardDBException(u'必须指定一个要插入的表名')
        else:
            fields = {'`%s`' % key:model.__dict__[key] for key in model.__dict__ 
                    if not key.startswith('_') and key not in without}
        gen_id = self.get_write_db(**kws).insert(self.gen_table_name(**kws), **fields)
        return gen_id
    
    def multi_insert(self, tablename, values):
        return self.get_write_db().multiple_insert(tablename, values=values)
    
    def update(self, **kws):
        keys, model, fields = kws.get('keys', ('id',)), kws['model'], kws.get('field_name', ())
        table = self.gen_table_name(**kws)
        # 构建where条件
        where_buffer = []
        where_vars = {}
        for key in keys:
            where_buffer.append("`%s`=$%s" % (key, key))
            where_vars[key] = model.__dict__[key]
        where = ','.join(where_buffer)
    
        # 构建更新字段信息,如果fields为空,那么更新model所涉及的所有字段
        # 否则只更新fields中指定的字段
        if fields:
            field_dict= {field:model.__dict__[field] for field in fields}
        else:
            field_dict = {field:model.__dict__[field] for field in model.__dict__ 
                   if not field.startswith('_')}
        
        return self.get_write_db(**kws).update(table, where=where, vars=where_vars, **field_dict)
    
    def delete(self, **kws):
        return self.get_write_db(**kws).delete(table=self.gen_table_name(**kws),
                 where=kws.get('where'), vars=kws.get('vars'))     

# SQL Patterns 元组的第一个参数为SQL正则, 第二个参数为是否是只读类型的SQL语句
_sql_patterns = [
        (re.compile(r'select.*?from\s+([^\s]*?)\s.*where.*', re.I),True),
        (re.compile(r'update\s+(.*?)\s+set.*?', re.I), False),
        (re.compile(r'delete\s+from\s+(.*?)\s+where.*', re.I), False),
        (re.compile(r'insert.*?into\s+(.*?)\s+.*', re.I), False)
]

class _DataAccessProxy(_BaseDataAccessProxy):
    
    def __init__(self, nodes):
        self._read_db_list, self._write_db = [], None
        for node in nodes:
            can_read, can_write = self.get_db_access(node)
            db = self.gen_db(node)
            if can_write:
                self._write_db = db
            if can_read:
                self._read_db_list.append(db)
    
    def get_read_db(self, **kws):
        return random.choice(self._read_db_list)
    
    def get_write_db(self, **kws):
        return self._write_db
    
    def query(self, sql, vars=None):
        sql = sql.strip()
        start = sql.split(' ', 1)[0]
        _db = None
        if start.lower() == 'select':
            _db = self.get_read_db()
        else:
            _db = self.get_write_db()
        return _db.query(sql_query=sql, vars=vars, processed=False)

class _ShardDataAccessProxy(_BaseDataAccessProxy):
    
    def __init__(self, nodes):
        self.read_db_lst, self.write_db_lst, self.max_hash = {}, {}, 0
        for node in nodes:
            node['shard_begin'], node['shard_end'] = int(node['shard_begin']), int(node['shard_end'])
            can_read, can_write = self.get_db_access(node)
            db = self.gen_db(node)
            if can_read:
                self.read_db_lst.setdefault(
                    (node['shard_begin'], node['shard_end']), []).append(db)
            if can_write:
                self.write_db_lst[(node['shard_begin'], node['shard_end'])] = db
            if node['shard_end'] > self.max_hash:
                self.max_hash = node['shard_end']
        self.max_hash += 1
        
    def get_hash(self, shard_value):
        return shard_value % self.max_hash
    
    def get_read_db(self, **kws):
        if 'shard' not in kws:
            raise ShardDBException(u'必须指定一个shard value!')
        node_hash = self.get_hash(kws['shard'])
        for scope in self.read_db_lst:
            if scope[0] <= node_hash <= scope[1]:
                return random.choice(self.read_db_lst[scope])
        raise ShardDBException(u'invalid node hash, shard value:%d, max hash:%d, \
                        node hash:%d' % (kws['shard'],self.max_hash,node_hash))
    
    def get_write_db(self, **kws):
        if 'shard' not in kws:
            raise ShardDBException(u'必须指定一个shard value!')
        node_hash  = self.get_hash(kws['shard'])
        for scope in self.write_db_lst:
            if scope[0] <= node_hash <= scope[1]:
                return self.write_db_lst[scope]
        raise ShardDBException(u'invalid node hash, shard value:%d, max hash:%d, \
                        node hash:%d' % (kws['shard'],self.max_hash,node_hash))
    
    def gen_table_name(self, **kws):
        table = _BaseDataAccessProxy.gen_table_name(self, **kws)
        if 'tablename_formatter' in kws:
            return kws['tablename_formatter'](ori_table=table, **kws)
        else:
            return ('%s_%0' + str(len(str(self.max_hash))) + 'd') % (table, self.get_hash(kws['shard']))
        
    def multi_insert(self):
        raise ShardDBException(u'shard数据源不支持批量插入!')
        

# 承载数据源代理的容器
class _DBContainer(object):
    '''可以同时用db.xxx和db["xxx"]的方式来访问数据源'''    
    def __getitem__(self, name):
        return self.__dict__[name]

db = _DBContainer()

def _load_nodes():
    global db
    common_cfg = {} # 普通节点配置
    shard_cfg = {} # shard节点配置
    with open(_db_cfg_file, 'r') as f:
        for line in f:
            line = line.strip()
            # 忽略空格和注释
            if not line or line.startswith('#'):
                continue
            node_cfg = json.loads(line, encoding="ASCII")
            # PooledDB传unicode编码的参数会出现奇怪问题
            node_cfg = {str(k):str(v) for k, v in node_cfg.items()}
            if 'shard_begin' in node_cfg:
                shard_cfg.setdefault(node_cfg['name'],[]).append(node_cfg)
            else:
                common_cfg.setdefault(node_cfg['name'], []).append(node_cfg)
    
    # deal commen nodes
    for name in common_cfg:
        setattr(db, name, _DataAccessProxy(common_cfg[name]))
    
    # deal shard nodes
    for name in shard_cfg:
        setattr(db, name, _ShardDataAccessProxy(shard_cfg[name]))
            
_load_nodes()