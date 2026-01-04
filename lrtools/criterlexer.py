#!/usr/bin/env python
# # # -*- coding: utf-8 -*-
# pylint: disable=line-too-long
"""
    Lexical parser for criteria
"""

import re


class CriterLexer:
    """
    Lexical parser for criteria
    """

    # List of tokens accepted after specific token
    RULES_FOLLOW = {
        None: ["LPAR", "KEYVAL"],
        "KEYVAL": ["OR", "AND", "RPAR"],
        "OR": ["KEYVAL", "LPAR"],
        "AND": ["KEYVAL", "LPAR"],
        "LPAR": ["KEYVAL", "LPAR"],
        "RPAR": ["OR", "AND", "RPAR"],
    }

    def __init__(self, criters):
        """ """
        self.criters = criters
        self.tokens = list()
        self.last_error = ""

    def _parse_keyval(self):
        """
        Parse KEY [= VALUE]
        """
        #
        # get criter
        #
        _m = re.match(r"(\w+) *", self.criters)
        if not _m:
            return False
        key = _m.group(1).lower()
        self.criters = self.criters[_m.end() :]

        #
        # get value
        #
        _m = re.match(r" *= *", self.criters)
        if _m:
            self.criters = self.criters[_m.end() :]
            # regex from https://www.metaltoad.com/blog/regex-quoted-string-escapable-quotes
            _m = re.match(
                r' *((?<![\\])[\'"])((?:.(?!(?<![\\])\1))*.?)\1', self.criters
            )
            if _m:
                # regex return quote type ("') and string
                value = _m.group(2)
            else:
                _m = re.match(r" *([^,\|\)\()]+)", self.criters)
                if _m:
                    value = _m.group(1)
                else:
                    self.last_error = f'No value for criterion "{key}"'
                    return False
            if _m:
                self.criters = self.criters[_m.end() :]
                self.tokens.append(("KEYVAL", (key, value)))

        else:
            # no value for criter
            value = "True"
            self.tokens.append(("KEYVAL", (key, value)))
        return True

    def parse(self, criters=None):
        """
        Parse criters string
        """
        if criters:
            self.criters = criters
        if not self.criters:
            return False

        while len(self.criters) > 0:

            self.criters = self.criters.rstrip()
            if len(self.criters) == 0:
                break

            #
            # parse "key = value"
            #
            if self._parse_keyval():
                continue
            if self.last_error:
                return False

            #
            # operator left parenthesis : '('
            #
            _m = re.match(r"(\() *", self.criters)
            if _m:
                self.tokens.append(("LPAR", None))
                self.criters = self.criters[_m.end() :]
                continue

            #
            # operator right parenthesis : ')'
            #
            _m = re.match(r"(\)) *", self.criters)
            if _m:
                self.tokens.append(("RPAR", None))
                self.criters = self.criters[_m.end() :]
                continue

            #
            # operator AND : ','
            #
            _m = re.match(r", *", self.criters)
            if _m:
                self.tokens.append(("AND", None))
                self.criters = self.criters[_m.end() :]
                continue

            #
            # operator OR : '|'
            #
            _m = re.match(r"\| *", self.criters)
            if _m:
                self.tokens.append(("OR", None))
                self.criters = self.criters[_m.end() :]
                continue

            #
            # Finally : token error
            #
            self.last_error = (
                f'Invalid token \042{self.criters.split(" ")[0]}\042'
            )

            return False

        return self.check_syntax()

    def check_syntax(self):
        """
        Check criters syntax (only following token)
        """
        prev_token = None
        par_level = 0
        for token, _ in self.tokens:
            allowed_tokens = self.RULES_FOLLOW[prev_token]
            if not token in allowed_tokens:
                self.last_error = f'"{token}" not allowed after "{prev_token}"'
                return False
            if token == "LPAR":
                par_level += 1
            elif token == "RPAR":
                par_level -= 1
            prev_token = token
        if par_level != 0:
            self.last_error = "unbalanced parenthesis"
            return False
        return True
