#
#  subunit: extensions to Python unittest to get test results from subprocesses.
#  Copyright (C) 2005  Robert Collins <robertc@robertcollins.net>
#
#  Licensed under either the Apache License, Version 2.0 or the BSD 3-clause
#  license at the users choice. A copy of both licenses are available in the
#  project source as Apache-2.0 and BSD. You may not use this file except in
#  compliance with one of these two licences.
#  
#  Unless required by applicable law or agreed to in writing, software
#  distributed under these licenses is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.  See the
#  license you chose for the specific language governing permissions and
#  limitations under that license.
#

"""Handlers for outcome details."""

from cStringIO import StringIO

import chunked, content, content_type


class DetailsParser(object):
    """Base class/API reference for details parsing."""


class SimpleDetailsParser(DetailsParser):
    """Parser for single-part [] delimited details."""

    def __init__(self, state):
        self._message = ""
        self._state = state

    def lineReceived(self, line):
        if line == "]\n":
            self._state.endDetails()
            return
        if line[0:2] == " ]":
            # quoted ] start
            self._message += line[1:]
        else:
            self._message += line

    def get_details(self, style=None):
        result = {}
        if not style:
            result['traceback'] = content.Content(
                content_type.ContentType("text", "x-traceback"),
                lambda:[self._message])
        else:
            if style == 'skip':
                name = 'reason'
            else:
                name = 'message'
            result[name] = content.Content(
                content_type.ContentType("text", "plain"),
                lambda:[self._message])
        return result

    def get_message(self):
        return self._message


class MultipartDetailsParser(DetailsParser):
    """Parser for multi-part [] surrounded MIME typed chunked details."""

    def __init__(self, state):
        self._state = state
        self._details = {}
        self._parse_state = self._look_for_content

    def _look_for_content(self, line):
        if line == "]\n":
            self._state.endDetails()
            return
        # TODO error handling
        field, value = line[:-1].split(' ', 1)
        main, sub = value.split('/')
        self._content_type = content_type.ContentType(main, sub)
        self._parse_state = self._get_name

    def _get_name(self, line):
        self._name = line[:-1]
        self._body = StringIO()
        self._chunk_parser = chunked.Decoder(self._body)
        self._parse_state = self._feed_chunks

    def _feed_chunks(self, line):
        residue = self._chunk_parser.write(line)
        if residue is not None:
            # Line based use always ends on no residue.
            assert residue == ''
            body = self._body
            self._details[self._name] = content.Content(
                self._content_type, lambda:[body.getvalue()])
            self._chunk_parser.close()
            self._parse_state = self._look_for_content

    def get_details(self, for_skip=False):
        return self._details

    def get_message(self):
        return None

    def lineReceived(self, line):
        self._parse_state(line)
