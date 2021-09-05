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

"""PTR lookup overrides read ShoDoHFlo

This reads from the Redis database maintained by ShoDoHFlo. ShoDoHFlo is
a DNS and netflow correlator: https://github.com/m3047/shodohflo

Configuration Parameters
------------------------

The following configuraiton parameters can be specified:

  redis_server  Address of the redis server. (required). It is assumed
                that the server is listening on the standard Redis port
                (6379).
  ttl           How long to keep associations cached. Defaults to 7200
                seconds (2 hours).
  max_assocs    Maximum number of associations to keep cached. Associations
                for which TTL has not expired may be deleted if the number
                of associations exceeds this value. Defaults to 5000
"""

import asyncio
import aioredis

from time import time
from random import random

from . import Superpower as SuperpowerBase
from .redis_data import get_all_clients, get_dns_data, DNSArtifact, CNAMEArtifact

TTL = 7200
MAX_ASSOCS = 5000

# These are the delays between started an entirely new refresh cycle, and refreshing
# individual clients, respectively.
CYCLE_DELAY = 10
CLIENT_DELAY = 1

class Clients(object):
    """All client IP addresses."""
    def __init__(self):
        self.clients = []
        return
    
class Association(object):
    """A single association."""
    def __init__(self, target, fqdns, ttl):
        self.target = target
        self.fqdns = fqdns
        self.ttl = ttl
        self.expires = self.expiry()
        self.orig_expires = self.expires
        return
    
    def expiry(self):
        """Compute the expiration timestamp."""
        return time() + self.ttl * (0.95 + 0.1 * random())
    
    def update(self, fqdns):
        self.fqdns = fqdns
        self.expires = self.expiry()
        return
    
    def moving(self):
        """A signal that expiry lists are being rotated."""
        self.orig_expires = self.expires
        return
    
    @property
    def updated(self):
        """True if expires is not equal to orig_expires."""
        return self.expires != self.orig_expires

class Associations(object):
    """All address/fqdn -> fqdn associations."""
    def __init__(self):
        # An Association is referenced in this index as well as in one of the
        # following expiry lists.
        self.index = {}
        # These lists are sorted in increasing order by Association.orig_expires.
        # When we need to eject things from cache, we process the entries in
        # self.expiry in order. It can happen that something is refreshed, in which
        # case Association.expires > Association.orig_expires. When processing an
        # entry, we use Association.expires. If Association.expires > now,
        # Association.orig_expires is set to Association.expires and the entry is
        # appended to self.new_expiry instead of being deleted. When self.expiry
        # is exhausted, self.new_expiry is sorted by Association.orig_expires and
        # replaces self.expiry.
        self.expiry = []
        self.new_expiry = []
        return
    
    def remove_one(self):
        """Called to move/remove one item.
        
        Returns True if the item was purged, False if it was moved to self.new_expiry.
        """
        item = self.expiry.pop(0)
        if item.updated:
            self.new_expiry.append(item)
            return
        del self.index[item.target]
        return
        
    def rotate_lists(self):
        """Promotes new_expiry to expiry."""
        for item in self.new_expiry:
            item.moving()
        self.expiry = sorted(self.new_expiry, key=lambda x:x.orig_expires)
        self.new_expiry = []
        return
        
    def purge(self):
        """Purge stuff from the cache which is expired/oldest.
        
        Stuff is purged which is older than TTL or if the total number of entries
        is in excess of MAX_ASSOCS.
        """
        if not self.index:
            return
        now = time()
        
        while self.expiry[0].orig_expires <= now or len(self.index) > MAX_ASSOCS:
            self.remove_one()
            if not self.expiry:
                if not self.index:
                    return
                self.rotate_lists()
        return
    
    def add(self, artifact, ttl):
        """Add an A / AAAA / CNAME record or update its TTL."""
        self.purge()
        
        target = ( isinstance(artifact, DNSArtifact)
               and str(artifact.remote_address) or artifact.name
                 ).lower().rstrip('.')
        fqdns = [ name.lower().rstrip('.') for name in artifact.onames ]

        if target in self.index:
            self.index[target].update(fqdns)
            return
        
        association = Association(target, fqdns, ttl)
        self.index[target] = association
        (self.new_expiry or self.expiry).append(association)
        
        return
    
    def get(self, k):
        return self.index.get(str(k), None)

class DictOfSets(dict):
    def add(self, k, v):
        if k not in self:
            self[k] = set()
        self[k].add(v)
        return
    
class Superpower(SuperpowerBase):
    """Check ShoDoHFlo's database."""

    def __init__(self, *args):
        SuperpowerBase.__init__(self, *args)
        self.associations = Associations()
        # Create a connection to the Redis database and cache it.
        self.ttl = self.config.get('ttl', TTL)
        self.max_assocs = self.config.get('max_assocs', MAX_ASSOCS)
        self.redis_host = self.config['redis_server']
        # Initialize the cache. We allow for event_loop to be None as a flag
        # that we're running (query) tests.
        if self.event_loop is not None:
            self.tasks.append(self.event_loop.create_task(self.init_cache()))
        return

    async def init_cache(self):
        self.redis = await aioredis.create_redis_pool('redis://'+self.redis_host)
        await self.refresh_cache(no_wait=True)
        self.event_loop.create_task(self.periodic_refresh())
        return
    
    async def refresh_cache(self, no_wait=False):
        clients = await get_all_clients(self.redis)
        for client in clients:
            if not no_wait:
                await asyncio.sleep(CLIENT_DELAY)
            # Only A / AAAA / CNAME derived data is returned.
            for rec in await get_dns_data(self.redis, client):
                self.associations.add(rec, self.ttl)
        return

    async def periodic_refresh(self):
        """Cache refresh.
        
        This task never exits.
        """
        started_cycle = time()
        while True:
            now = time()
            if (now - started_cycle) < CYCLE_DELAY:
                await asyncio.sleep(CYCLE_DELAY - (now - started_cycle) + 1)
            started_cycle = time()
            await self.refresh_cache()
        # Never exits.
    
    def follow_chains(self, root, chains):
        associations = self.associations.get(root[-1])
        if associations is None:
            if len(root) > 1:
                chains.append(root.copy())
            return
        for association in associations.fqdns:
            if association in root and root not in chains:
                chains.append(root.copy())
                return
            self.follow_chains(root + [association], chains)
        return
    
    @staticmethod
    def match_len(chain):
        """What is the common TLD?"""
        previous,current = chain[-2:]
        previous = [ x for x in reversed(previous.split('.')) ]
        current = [ x for x in reversed(current.split('.')) ]

        max_length = min(( len(x) for x in (previous,current) ))
        i = 0
        while i < max_length:
            if previous[i] != current[i]:
                return i
            i += 1
        return i
            
    def query(self, address):
        # Get all possible chains.
        chains = []

        self.follow_chains([address], chains)
        # None?
        if not chains:
            return ''
        
        # Only one?
        if len(chains) == 1:
            return chains[0][-1]
        
        # Look for the longest chain.
        lengths = DictOfSets()
        for i,chain in enumerate(chains):
            lengths.add(len(chain), i)
        max_length = max(lengths.keys())
        
        if len(lengths[max_length]) == 1:
            return chains[lengths[max_length].pop()][-1]
        
        # Look for the one with the least matching labels / most different domain.
        # This only works if there is at least one CNAME in the chain.
        candidates = list(lengths[max_length])
        
        if max_length >= 2:
            lengths = DictOfSets()
            for i,candidate in enumerate(candidates):
                lengths.add(self.match_len(chains[candidate]), i)
            min_match = min(lengths.keys())
            if len(lengths[min_match]) == 1:
                return chains[candidates[lengths[min_match].pop()]][-1]
        
        # Look for the least number of labels.
        candidates = list(lengths[min_match])

        lengths = DictOfSets()
        for i,candidate in enumerate(candidates):
            lengths.add(len(chains[candidate][-1]), i)
        min_length = min(lengths.keys())

        # If there's more than one it really doesn't matter which one
        # we return.
        return chains[candidates[lengths[min_length].pop()]][-1]
