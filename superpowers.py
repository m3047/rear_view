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

"""TCP Only DNS Forwarder with Superpowers

Invoke as root:

    superpowers.py {--tls} <udp-listen-address> <remote-server-address>
    
Parameters:

    --tls       When specified uses DoT and contacts the DNS server on port 853
    udp-listen  This is the address to listen on for dns request. It will be
                127.0.0.1 most of the time.
    remote-serv This is the address of your recursive resolver. It will be
                contacted with a TCP connection rather than UDP.
                
Once it's running, use it as a (the only) nameserver in your network configuration.

This DNS forwarder attempts to rewrite PTR answers using a variety of mechanisms.
For all other requests, including as a fallback when its own local efforts fail,
it will attempt to make a TCP connection to the recursive resolver.

"Superpowers" refers to the ability to intercept and rewrite PTR queries as are
typically performed by default by the many tools I use which I commonly postscript
with "-n": arp, route, netstat, iptables....

Configuration is loaded from configuration.yaml. See "pydoc3 superpowers" for further
information on configuration file format.
"""

import sys
from os.path import dirname
import asyncio
import ssl

import dns.message
import dns.rrset
import dns.rcode

from superpowers import *

TTL = 60

class SuperUDPListener(asyncio.DatagramProtocol):
    """Here's where we get our superpowers by intermediating PTR requests."""
    
    def __init__(self):
        asyncio.DatagramProtocol.__init__(self)
        self.config = None
        return
    
    def connection_made(self, transport):
        self.transport = transport
        return

    async def handle_request(self, request, addr):
        if self.config is None:
            self.config = Config(load_config(self.exec_dir), self.event_loop)
        powers = Powers(self.config, request)

        # first / last / always / never is sorted out here.
        if powers() and powers.mode in ('first', 'always'):
            if not powers.ready:
                await powers.marshall()
            if powers.exec():
                dns_response = dns.message.make_response(powers.query, recursion_available=True)
                dns_response.answer.append( dns.rrset.from_text_list( dns_response.question[0].name, TTL, 'IN', 'PTR', [ powers.response ] ))
                self.transport.sendto(dns_response.to_wire(), addr)
                return
        if not powers() or powers.mode != 'always':
            reader, writer = await asyncio.open_connection(self.remote_address, self.ssl and 853 or 53, ssl=self.ssl)
            # NOTE: When using TCP the request and response are prepended with
            # the length of the request/response.
            writer.write(len(request).to_bytes(2, byteorder='big')+request)
            await writer.drain()
            
            response_length = int.from_bytes(await reader.read(2), byteorder='big')
            response = b''
            while response_length:
                resp = await reader.read(response_length)
                if not len(resp):
                    break
                response += resp
                response_length -= len(resp)
            
            writer.close()
            dns_response = dns.message.from_wire(response)
            if dns_response.rcode() == 0 or not powers() or powers.mode == 'never':
                self.transport.sendto(response, addr)
                return
        if powers() and powers.mode == 'last':
            if not powers.ready:
                await powers.marshall()
            if powers.exec():
                dns_response = dns.message.make_response(powers.query, recursion_available=True)
                dns_response.answer.append( dns.rrset.from_text_list( dns_response.question[0].name, TTL, 'IN', 'PTR', [ powers.response ] ))
                self.transport.sendto(dns_response.to_wire(), addr)
                return
        
        # If we're still hanging around then use the fallback value.
        if powers() and powers.fqdn.strip('.'):
            dns_response = dns.message.make_response(powers.query, recursion_available=True)
            dns_response.answer.append( dns.rrset.from_text_list( dns_response.question[0].name, TTL, 'IN', 'PTR', [ powers.fqdn ] ))
            self.transport.sendto(dns_response.to_wire(), addr)
            return
        
        # If we're still here, return NXDOMAIN.
        dns_response = dns.message.make_response(powers.query, recursion_available=True)
        dns_response.set_rcode(dns.rcode.NXDOMAIN)
        self.transport.sendto(dns_response.to_wire(), addr)

        return
    
    def datagram_received(self, request, addr):
        self.event_loop.create_task(self.handle_request(request,addr))
        return

def main(Listener):
    try:
        tls = sys.argv[1] == '--tls'
        if tls:
            listen_address, remote_address = sys.argv[2:4]
        else:
            listen_address, remote_address = sys.argv[1:3]
    except:
        print('Usage: superpowers.py {--tls} <udp-listen-address> <remote-server-address>', file=sys.stderr)
        sys.exit(1)
    event_loop = asyncio.get_event_loop()
    listener = event_loop.create_datagram_endpoint(Listener, local_addr=(listen_address, 53))
    try:
        transport, service = event_loop.run_until_complete(listener)
    except PermissionError:
        print('Permission Denied! (are you root?)', file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print('{} (did you supply a loopback address?)'.format(e), file=sys.stderr)
        sys.exit(1)
        
    service.event_loop = event_loop
    service.remote_address = remote_address
    service.exec_dir = dirname(sys.argv[0])
    
    if tls:
        service.ssl = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    else:
        service.ssl = None

    try:
        event_loop.run_forever()
    except KeyboardInterrupt:
        pass

    transport.close()
    event_loop.close()

if __name__ == "__main__":
    main(SuperUDPListener)
