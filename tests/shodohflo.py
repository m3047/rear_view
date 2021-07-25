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

import sys
import unittest

if '..' not in sys.path:
    sys.path.insert(0,'..')

import superpowers.shodohflo as shodohflo

class TestQuery(unittest.TestCase):
    """Tests query rules for the ShoDoHFlo superpower."""
    
    def setUp(self):
        self.superpower = shodohflo.Superpower({'redis_server':''}, None)
        return
    
    def define_associations(self, *associations):
        for association in associations:
            self.superpower.associations.index[association[0]] = \
                shodohflo.Association(association[0], association[1], 60)
        return
        
    def test_not_found(self):
        """Tests if the IP address is not found."""
        result = self.superpower.query('1.2.3.4')
        self.assertEqual(result, '')
        return
    
    def test_only_one(self):
        """Tests what happens if there is only one answer."""
        self.define_associations(
                ('1.2.3.4',              ['example.com'])
            )
        result = self.superpower.query('1.2.3.4')
        self.assertEqual(result, 'example.com')
        return
    
    def test_only_one_chain(self):
        """Tests what happens if there is only one CNAME chain."""
        self.define_associations(
                ('1.2.3.4',              ['x.example.com']),
                ('x.example.com',        ['example.com'])
            )
        result = self.superpower.query('1.2.3.4')
        self.assertEqual(result, 'example.com')
        return

    def test_longest_chain(self):
        """Tests preference for the longest chain."""
        self.define_associations(
                ('1.2.3.4',              ['x.example.com','y.example.com']),
                ('x.example.com',        ['example.com'])
            )
        result = self.superpower.query('1.2.3.4')
        self.assertEqual(result, 'example.com')
        return

    def test_different_domain(self):
        """Tests preference for CNAMEs changing to a different domain."""
        self.define_associations(
                ('1.2.3.4',              ['x.example.com']),
                ('x.example.com',        ['example.com','another-example.com'])
            )
        result = self.superpower.query('1.2.3.4')
        self.assertEqual(result, 'another-example.com')
        return
    
    def test_least_labels(self):
        """Tests preference for the least number of labels."""
        self.define_associations(
                ('1.2.3.4',              ['x.example.com','example.com','y.example.com'])
            )
        result = self.superpower.query('1.2.3.4')
        self.assertEqual(result, 'example.com')
        return
    
    def test_loop_detection(self):
        """Test ability to detect loops."""
        self.define_associations(
                ('1.2.3.4',             ['example.com']),
                ('example.com',         ['foo.example.com']),
                ('foo.example.com',     ['example.com'])
            )
        result = self.superpower.query('1.2.3.4')
        self.assertEqual(result, 'foo.example.com')
        return

if __name__ == '__main__':
    unittest.main(verbosity=2)
