# `PTR` records explained

`PTR` records, also called "Reverse DNS", are part of the _DNS_ system specification. While `A` (IP4) and `AAAA` (IP6) queries look up addresses from names like
`www.example.com`, `PTR` records are intended to do the opposite.

You may be familiar with `dig -x` which provides a `PTR` lookup for a given address. In point of fact the (distributed) database
which is queried is another DNS tree (just like the one which has e.g. `.com`, `.net`, `.us` and so forth as its toplevel "leaves"),
with different roots.

Here are some real examples from my local network:

```
# dig sophia.m3047

;; ANSWER SECTION:
SOPHIA.m3047.           600     IN      A       10.0.0.224

;; AUTHORITY SECTION:
m3047.                  600     IN      NS      ATHENA.m3047.

 # dig -x 10.0.0.224

;; ANSWER SECTION:
224.0.0.10.in-addr.arpa. 600    IN      PTR     SOPHIA.M3047.

;; AUTHORITY SECTION:
0.10.in-addr.arpa.      3600    IN      NS      ATHENA.M3047.

# dig 224.0.0.10.in-addr.arpa PTR

;; ANSWER SECTION:
224.0.0.10.in-addr.arpa. 600    IN      PTR     SOPHIA.M3047.

;; AUTHORITY SECTION:
0.10.in-addr.arpa.      3600    IN      NS      ATHENA.M3047.
```

## Notoriously inaccurate

`PTR` records are notoriously inaccurate, for the following reasons.

### Ignorance

People are ignorant about the mere existence of `PTR` records and how they are implemented.

They tend not to get updated, or paid attention to when they're incorrect. One of the rude
awakenings (there are others) people have about `PTR` records is when they try to run their
own mail server. It's not in the mail delivery standards, but for spam filtering purposes
there is a general presumption that "valid infrastructure == valid reverse DNS" and so you
have to get reverse DNS (a `PTR` record) set up for your mail server's address.

### Independent delegation

Although both are tracked in distributed databases collectively referred to as "the DNS", in
fact a name like `www.example.com` is delegated from `example.com` which is in turn delegated
from `.com` which is in turn delegated from "root". However an address like `10.0.0.224`, reversed
to `224.0.0.10.in-addr.arpa` (the key where the `PTR` record lives) is delegated from `0.0.10.in-addr.arpa`
and so forth.

Technically speaking `.arpa` is a "top level domain" (TLD) under the same DNS root as `.com`, `.net` and
so forth but all it stores is pointer records.

Unless you run your own DNS, we can assume your domain registrar runs DNS services for you: they
_delegate_ that domain to you and are in turn authorized to edit it as delegees from whatever TLD
your domain lives under.

The address on the other hand is provided by whomever hosts your server, and one or more addresses
were delegated to them by an upstream bandwidth provider. Now you have to figure out who actually
controls the delegation (your provider or their upstream) and convince them to edit the `PTR`
record on your behalf.

### Multiple names

Just like the DNS allows you to provide multiple addresses when looking up a domain name, technically
it allows you to specify multiple `PTR` records, in practice that doesn't work very well.

Although `PTR` records are poor security (see _Lyin' liars_ below) they have historically been
utilized for access control. The tools which utilize `PTR` records generally do a poor job of
dealing with multiple answers.

### `CNAME` chains

A `CNAME` is a way to create aliases which point to a different name. Functionally the following two
are equivalent when looking up an address for a domain name:

**multiple `A` records**

```
host_a.example.com         A      1.2.3.4
host_b.example.com         A      1.2.3.4
```
Assuming you have correct `PTR` records in practice you are going to have to pick one host,
either `host_a` or `host_b`, for the "owner" of `1.2.3.4`.

**using `CNAME` records**

```
big_server.example.com     A      1.2.3.4
host_a.example.com         CNAME  big_server.example.com.
host_b.example.com         CNAME  big_server.example.com.
```

In this case the `PTR` record presumably uses `big_server` for the owner of `1.2.3.4` so
you'll never see that it hosts either `host_a` or `host_b`.

### Lyin' liars

And of course people just lie. They don't care, or they're trying to evade (poor) security by
impersonating a different host.
