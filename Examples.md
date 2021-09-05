# Examples

## The config file

For simplicity and dramatic effect, we're only using _ShoDoHFlo_ here.

```
params:
  shodohflo: { redis_server: 'sophia.m3047' }
subnets:
  - powers: ['shodohflo']
    nets:
      - 10.0.0.128/25   last   office-routable
      - 10.0.0.0/25     last   office-norouting
      - net:  10.0.1.0/24
        mode: last
        fqdn: media-network
      - 10.0.0.0/23     last   locally-assigned
      - 0.0.0.0/0       first
```

## An address which is in use on the local network

`10.0.0.220` is locally assigned and has an FQDN.

```
# dig sophia.m3047 +noall +answer +comments 

; <<>> DiG 9.12.3-P1 <<>> sophia.m3047 +noall +answer +comments
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 16859
;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 1, ADDITIONAL: 2

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
; COOKIE: 6bf084286603f194205105986134fa2dd04a3e3e462d1cf9 (good)
;; ANSWER SECTION:
SOPHIA.m3047.           600     IN      A       10.0.0.224

# dig -x 10.0.0.224 +noall +answer +comments

; <<>> DiG 9.12.3-P1 <<>> -x 10.0.0.224 +noall +answer +comments
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 56161
;; flags: qr aa rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 1, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
; COOKIE: 8bda6cda7a6c17242dd12a056134fa2f83f6b3db846446df (good)
;; ANSWER SECTION:
224.0.0.10.in-addr.arpa. 600    IN      PTR     SOPHIA.M3047.
```

## An address which is not in use on the local network

```
# dig -x 10.0.0.23 +noall +answer +comments

; <<>> DiG 9.12.3-P1 <<>> -x 10.0.0.23 +noall +answer +comments
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 57024
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 8192
;; ANSWER SECTION:
23.0.0.10.in-addr.arpa. 60      IN      PTR     office-norouting.
```

## Using ShoDoHFlo to dynamically create PTR data

#### This address does not have a PTR record

This address does not have a `PTR` record but it does resolve an FQDN, as you will see.

```
# dig -x 151.101.53.67 +noall +answer +comments

; <<>> DiG 9.12.3-P1 <<>> -x 151.101.53.67 +noall +answer +comments
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NXDOMAIN, id: 65389
;; flags: qr rd ra; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 8192
```

#### The unsurprising result with tcpdump

```
# tcpdump -ieth0 dst host 151.101.53.67
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on eth0, link-type EN10MB (Ethernet), capture size 262144 bytes
09:41:11.217104 IP sophia.m3047 > 151.101.53.67: ICMP echo request, id 14306, seq 1, length 64
09:41:12.218878 IP sophia.m3047 > 151.101.53.67: ICMP echo request, id 14306, seq 2, length 64
```

#### Let's resolve that...

Turns out that `www.cnn.com` resolves to that address via a `CNAME`. A `PTR` record would be useless here...

```
 dig www.cnn.com +noall +answer +comments                

; <<>> DiG 9.12.3-P1 <<>> www.cnn.com +noall +answer +comments
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 61159
;; flags: qr rd ra; QUERY: 1, ANSWER: 2, AUTHORITY: 4, ADDITIONAL: 5

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
; COOKIE: a141d63f40ad042219bba8a36134f33e924c800c6702354e (good)
;; ANSWER SECTION:
www.cnn.com.            300     IN      CNAME   turner-tls.map.fastly.net.
turner-tls.map.fastly.net. 30   IN      A       151.101.53.67
```

#### The tcpdump surprise

But now when we run _tcpdump_ look what happens:

```
# tcpdump -ieth0 dst host 151.101.53.67
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on eth0, link-type EN10MB (Ethernet), capture size 262144 bytes
09:42:04.888886 IP sophia.m3047 > www.cnn.com: ICMP echo request, id 14329, seq 1, length 64
09:42:05.890879 IP sophia.m3047 > www.cnn.com: ICMP echo request, id 14329, seq 2, length 64
```

That result is confirmed by `dig`:

```
# dig -x 151.101.53.67 +noall +answer +comments

; <<>> DiG 9.12.3-P1 <<>> -x 151.101.53.67 +noall +answer +comments
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 43109
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 8192
;; ANSWER SECTION:
67.53.101.151.in-addr.arpa. 60  IN      PTR     www.cnn.com.
```
