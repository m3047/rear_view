# Superpowers!

**STATUS: solid alpha ("works on my machines, should generalize")**

There are all kinds of systemly utilities which helpfully try reverse DNS lookup on addresses. It's useless;
I'm always using `-n`. `netstat -n`, `iptables -n`, you get the idea.

Let's try to fix PTR lookups!

How do we do that? BY RETURNING USEFUL INFORMATION! Seems kinda obvious to me...

_Superpowers_ refers to the ability to read minds and bend spoons (coming soon!).

But until then I have the basics. You can create defaults which will be returned if the normal `PTR` lookup
fails; I explain below.

This project "embraces and extends" [tcp_only_forwarder](https://github.com/m3047/tcp_only_forwarder).

`superpowers.py` runs just like `forwarder.py` except that it has a `superpowers.yaml` config file where
you can take control of PTR lookups.

### Invocation

Invoke as root:

    superpowers.py {--tls} <udp-listen-address> <remote-server-address>
    
Parameters:

    --tls       When specified uses DoT and contacts the DNS server on port 853
    udp-listen  This is the address to listen on for dns request. It will be
                127.0.0.1 most of the time.
    remote-serv This is the address of your recursive resolver. It will be
                contacted with a TCP connection rather than UDP.

Once it's running, update your network configuration using the listen address (`127.0.0.1` in
this example) as a (the only) nameserver.

This DNS forwarder attempts to rewrite PTR answers using a variety of mechanisms.
For all other requests, including as a fallback when its own local efforts fail,
it will attempt to make a TCP connection to the recursive resolver.

### Additional resources

* [PTR records explained](https://github.com/m3047/rear_view/blob/main/Ptr_Records_Explained.md)
* [Some examples](https://github.com/m3047/rear_view/blob/main/Examples.md)

## Configuring `superpowers.yaml`

**If you're trying to use this in its alpha state, please reach out to me at consulting@m3047.net** I'm not going
to try to sell you anything, I will try to help.

The `params` section probably gives the plot away in terms of what superpowers are planned. ;-) Leave it alone
for now. What you can configure today is the `subnets` section. `pydoc3 superpowers` should give you the
complete documentation.

TLDR, the powers available are:

* **hard coded** in the configuration file
* **sqlite** which uses a _sqlite_ database (see `pydoc3 superpowers.sqlite`)
* **shodohflo** which uses a [ShoDoHFlo](https://github.com/m3047/shodohflo) database for dynamic discovery of assets

The _hard coded_ option is always enabled. You can enable either or both of the other two options by setting them
in `powers:`:

```
  - powers: ['sqlite']
```

Leave the `powers:` empty (for now). Although an example is provided with the three keys, you can simple
specify nets as a subnet + mode + default string. Since there is no other reason to define things in here,
you don't need to worry about entries without an _fqdn_.

Furthermore, because there are no powers just leave the _mode_ as `last`. Just define some subnets and fqdn-like
strings.

Then run `superpowers.py` and configure it as your local resolver. If you want it test it without changing your
configuration, then use something like `dig @127.0.0.1 -x 10.0.0.22` to see what's happening.

## Security Issues / Side Effects

Some programs use or allow the use of DNS names for access control. (This is not really good security, especially without DNSSEC.)

If the program performs a forward lookup of the DNS name and uses the ip address for comparison, all is good.
If however the program performs a reverse lookup of the connecting address and compares the returned fqdn
against the configured value, _superpowers_ can most definitely interfere.

### Single Process Overrides using [cwrap](https://cwrap.org/)

If you happen to run some kind of service on the box which does need the "legitimate" reverse lookups,
you can use _cwrap_ to define a process-level name resolution policy. _Cwrap_ was originally created by the
_Samba_ team as a testiung tool.

You can either make the systemwide defaults _superpowers_ and implement a process-level override for
the process which needs the legitimate responses, or you can do it the other way around.

## Big Plans

This is a concept piece which explores several options for achieving the desired functionality.

I also plan to eventually implement a service which integrates with _BIND_ using _Dnstap_ to populate a
_Response Policy Zone_ with `PTR` records... in this case using the _RPZ_ as a source of truth rather
than as a ban hammer.

## Use Cases

PTR record lookup is a "backdoor" we can utilize to increase the utility of existing tools instead of having to cut & paste into another tool to find out about an address. You can disable it in most tools with -n (that's how I use most of them most of the time), so it's a way to make a mode I seldom use customizable to increase usefulness.

If you write / have a tool that supports PTR lookups, it's the "integration to rule them all" for getting your IoCs into those tools (see the sqlite power as an example).

ShoDoHFlo in particular collapses CNAME chains and so addresses the increasingly prevalent case where PTR record are normally of no great use, instead offering the name which was actually looked up

Imagine something like [EtherApe](https://etherape.sourceforge.io/) or your favorite graphical netflow tool with enhanced reverse lookups:
![etherape](etherape.png)
