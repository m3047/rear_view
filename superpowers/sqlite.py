#!/usr/bin/python3
# Copyright (c) 2021 by Fred Morris Tacoma WA
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""PTR lookup overrides read from a sqlite database.

The database consists of a single table named Address with two fields:

 * address -- the address
 * fqdn    -- the fqdn to return.

Both fields are strings.

Configuration Parameters
------------------------

The following configuration parameters can be specified:

  db    The path to the database file. (required)
"""

import os.path
from sqlite3 import dbapi2 as sqlite3

from . import Superpower as SuperpowerBase

SCHEMA = """
CREATE TABLE Address (
    address TEXT PRIMARY KEY,
    fqdn    TEXT
);
"""

class Superpower(SuperpowerBase):
    """Check a sqlite database."""

    def __init__(self, *args):
        SuperpowerBase.__init__(self, *args)
        # Create the db if it doesn't exist.
        initialize_db = not os.path.isfile(self.config['db'])
        self.db = sqlite3.connect(self.config['db'])
        if initialize_db:
            self.db.cursor().executescript(SCHEMA)
            self.db.commit()
        self.db.row_factory = sqlite3.Row
        return
    
    def query(self, address):
        cur = self.db.execute("SELECT fqdn FROM Address where address = ?", (str(address),))
        rec = cur.fetchone()
        return rec is not None and rec[0] or ''
        