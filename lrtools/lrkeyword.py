#!python3
# # -*- coding: utf-8 -*-
# pylint: disable=line-too-long

'''
LRKeywords class for Lightroom keywords manipulation
'''

class LRKeywords():
    '''
    Keywords manipulation
    '''
    def __init__(self, lrdb):
        '''
        Init
        - lrdb : LRCatDB instance
        '''
        self.lrdb = lrdb
        self.tree = None
        self.rootid = None
        self.id2keyname = None
        self.hierachical_keywords = None


    def _init_hierarchical_keywords(self):
        '''
        Initialize and build  hierarchical keywords
        '''
        self.lrdb.cursor.execute('SELECT id_local, name, parent FROM AgLibraryKeyword')
        self.tree = {}
        self.id2keyname = {}
        for pid, name, parent in self.lrdb.cursor.fetchall():
            if not name:
                name = ''
            self.id2keyname[pid] = name
            if not parent:
                self.rootid = pid
                parent = ''
            if parent not in self.tree:
                self.tree[parent] = []
            self.tree[parent].append(pid)

        # creation dictionnaire index clé vers nom hierachique
        self.hierachical_keywords = self._build_hierachical_keywords()



    def _showtree(self, pid, level):
        '''
        Display keywords in hierachical format
        '''
        if not self.tree:
            self._init_hierarchical_keywords()
        if not pid:
            pid = self.rootid
        for k in self.tree[pid]:
            print(level * ' ', self.id2keyname[k])
            if k in self.tree:
                self._showtree(k, level + 2)

    def show_hierarchical_indented(self):
        '''
        Display keywords in hierachical indented format
        '''
        self._showtree(self.rootid, 0)

    def _build_hierachical_keywords(self):
        '''
        Build list of keywords in hierachical form
        '''
        def _build(pid, hname, hkeys):
            hname_next = hname
            if hname:
                hname_next += '|'
            for k in self.tree[pid]:
                if k in self.tree:
                    _build(k, f"{hname_next}{self.id2keyname[k]}", hkeys)
                hkeys[k] = f"{hname_next}{self.id2keyname[k]}"
        if not self.tree:
            self._init_hierarchical_keywords()
        hkeywords = {}
        _build(self.rootid, '', hkeywords)
        return hkeywords

    def get_hierarchical_list(self):
        '''
        Return hierarchical list sorted by keywords
        '''
        if not self.hierachical_keywords:
            self._init_hierarchical_keywords()
        return sorted(self.hierachical_keywords.values())

    def get_hierarchical_name(self, idkey):
        '''
        Return hierarchical name of key index
        '''
        if not self.hierachical_keywords:
            self._init_hierarchical_keywords()
        return self.hierachical_keywords[idkey]

    def get_name(self, idkey):
        '''
        Return name of key index
        '''
        if not self.hierachical_keywords:
            self._init_hierarchical_keywords()
        return self.hierachical_keywords[idkey].split('|')[-1]

    def all_persons(self):
        ''' Select all persons keywords '''
        self.lrdb.cursor.execute('SELECT name FROM AgLibraryKeyword WHERE keywordType="person" ORDER BY name')
        return self.lrdb.cursor.fetchall()

    def photo_keys(self, idphoto, include_persons=True):
        '''
        Get photo keywords

        Parameters:
            idphoto : (int) local_id from table Adobe_Image
            include_persons : (bool) include keywordType="person" if True
        Return :
            list_hierarchical_keywords , list_keywords
        '''
        keynames = []
        hkeynames = []
        if include_persons:
            self.lrdb.cursor.execute(f'SELECT tag FROM AgLibraryKeywordImage WHERE image={idphoto}')
            for idkey, in self.lrdb.cursor.fetchall():
                hkeynames.append(self.get_hierarchical_name(idkey))
                keynames.append(self.get_name(idkey))
        else:
            self.lrdb.cursor.execute(f'SELECT tag, name, keywordType FROM AgLibraryKeywordImage ki JOIN AgLibraryKeyword k ON ki.tag = k.id_local WHERE image={idphoto}')
            for idkey, name, ktype in self.lrdb.cursor.fetchall():
                if ktype == 'person':
                    continue
                hkeynames.append(self.get_hierarchical_name(idkey))
                keynames.append(name)
        return hkeynames, keynames


    def hierachical_indexes(self, key_part, operation):
        '''
        Find keywords containing key_part, and returns all keyword indexes hierachically under theses keywords
        - key_part : (str) keyword or part of keyword without joker '%'
        - operation : operation of smart function. Can be: all, any, noneOf, words, beginsWith, endsWith
            * words : find complete word in keywords (ex: key_part="sport", returns "sport", "professional sport" , but not "sporting", "transport")
            * beginsWith : complete word in each keyword begins with key_part
            * endsWith : complete word in each keyword ends with key_part
            * all, any, noneOf : find all occurences of key_part in keywords
        '''
        key_part = key_part.lower()
        key = f'"%{key_part}%"'

        def find_sub_indexes(index, indexes):
            self.lrdb.cursor.execute(f'SELECT id_local FROM AgLibraryKeyword WHERE parent = {index}')
            sub_indexes = self.lrdb.cursor.fetchall()
            for sub_index, in sub_indexes:
                indexes.append(int(sub_index))
                find_sub_indexes(int(sub_index), indexes)

        if operation == 'words':
            self.lrdb.cursor.execute(f'SELECT id_local, lc_name FROM AgLibraryKeyword WHERE lc_name LIKE {key}')
            rows = []
            for row in self.lrdb.cursor.fetchall():
                # check if complete word in keyword
                if key_part.lower() in row[1].split():
                    rows.append((row[0],))
        elif operation == 'endsWith':
            self.lrdb.cursor.execute(f'SELECT id_local, lc_name FROM AgLibraryKeyword WHERE lc_name LIKE {key}')
            rows = []
            for row in self.lrdb.cursor.fetchall():
                for word in row[1].split():
                    if word.endswith(key_part):
                        rows.append((row[0],))
        elif operation == 'beginsWith':
            self.lrdb.cursor.execute(f'SELECT id_local, lc_name FROM AgLibraryKeyword WHERE lc_name LIKE {key}')
            rows = []
            for row in self.lrdb.cursor.fetchall():
                for word in row[1].split():
                    if word.startswith(key_part):
                        rows.append((row[0],))
        else:
            rows = self.lrdb.cursor.execute(f'SELECT id_local FROM AgLibraryKeyword WHERE lc_name LIKE {key}').fetchall()
        if not rows:
            return []
        indexes = []
        for row in rows:
            key_part, = row
            indexes += [key_part]
            find_sub_indexes(key_part, indexes)
        return indexes
