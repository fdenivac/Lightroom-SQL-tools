#!/usr/bin/env python
# # -*- coding: utf-8 -*-
# pylint: disable=bad-continuation,line-too-long, C0326

'''
LRSelectPhoto class for building SQL select for table Adobe_images
'''


from .lrselectgeneric import LRSelectGeneric

class LRSelectCollection(LRSelectGeneric):
    '''
    Build select request for collection table AgLibraryCollection
    '''

    MAIN_TABLE = 'AgLibraryCollection col'

    def __init__(self, lrdb):
        '''
        '''
        super().__init__(lrdb, \
            #
            # Table source
            #
            'AgLibraryCollection col', \

            #
            # Column description
            #
            { \
                'all' :  {
                    'True' : [ '*',  None ] }, \
                'name' : { \
                    'True' : [ 'col.name AS name',  None ] }, \
                'id' : { \
                    'True' : [ 'col.id_local AS id',  None ] }, \
                'type' : { \
                    'True' : [ 'col.creationId AS type',  None ] }, \
                'parent' : { \
                    'True' : [ 'col.parent AS parent',  None ] }, \
                'smart' : { \
                    'True' : ['cont.content AS content', [ 'JOIN AgLibraryCollectionContent cont ON col.id_local = cont.collection' ] ] }, \
            },

            #
            # Criteria description
            #
            { \
                'name' : [ \
                    '', \
                    'col.name LIKE "%s"', \
                    ],
                'id' : [ \
                    '', \
                    'col.id_local = %s', \
                    ],
                'type' : [ \
                    '', \
                    '%s', self.func_type, \
                    ],
                'id4smart' : [
                    'JOIN AgLibraryCollectionContent cont ON col.id_local = cont.collection', \
                    'col.id_local=%s AND cont.owningModule = "ag.library.smart_collection"',
                    ],
                'name4smart' : [
                    'JOIN AgLibraryCollectionContent cont ON col.id_local = cont.collection', \
                    'col.name LIKE "%s" AND cont.owningModule = "ag.library.smart_collection"',
                    ],
              }
        )


    def func_type(self, value):
        ''' convert value for "type" criteria (creationId) '''
        if value == 'standard':
            return 'creationId="com.adobe.ag.library.collection"'
        if value == 'smart':
            return 'creationId="com.adobe.ag.library.smart_collection"'
        if value == 'all':
            return 'creationId="com.adobe.ag.library.smart_collection" OR creationId="com.adobe.ag.library.collection"'
        else:
            return 'creationId="%s"' % value



    def select_generic(self, columns, criters, **kwargs):
        '''
        Build SQL request for collecion table (AgLibraryCollection) from key/value pair
        columns :
            - 'name'      : collection name
            - 'id'        : id collection
            - 'type'      : collection type
            - 'parent'    : id of parent collection
            - 'smart'     : data of smart collection. For a specfic collection use criteria "id4content" or "name4content"
        criteria :
            - 'name'      : (str) collection name
            - 'id'        : (int) collection id
            - 'type'      : (str) collection type (creationId) : "standard", "smart", "all", or explicit creationId content (as com.adobe.ag.library.group)
            - 'id4smart  ': (int) id smart collection. To be used with column "smart"
            - 'name4smart': (str) name of smart collection. To be used with column "smart"
        kwargs :
            - print : print sql and return None
            - sql : return SQL string only
        '''

        if not columns:
            columns = 'name'
        return super().select_generic(columns, criters, **kwargs)
