#!/usr/bin/env python3
"""Simulacion logica del Caso E (DMZ corporativa protegida).

Modela la capa 3 de docs/especificacion.md:
  - tablas de rutas: conectadas, estaticas y OSPFv2/OSPFv3 (un salto, area 0)
  - ACL sin estado de los routers Cisco (con contadores por linea)
  - FortiGate con estado: VIP 1:1, SNAT, politicas en orden, denegacion
    implicita, local-in (allowaccess + trusted hosts), sesiones y logs
  - bind9 autoritativo con vistas (split horizon) y nginx
Luego ejecuta la matriz de pruebas del documento y pruebas extra.

No reemplaza GNS3: no modela capa 2, temporizadores, ND/ARP real ni
particularidades de las imagenes (licencia del FortiGate, Docker, etc.).
"""
import ipaddress as ipa
import sys
from dataclasses import dataclass, field, replace

sys.stdout.reconfigure(encoding="utf-8")


def net(s):
    return ipa.ip_network(s, strict=False)


def addr(s):
    return ipa.ip_address(s)


def eui64(prefix, mac):
    b = [int(x, 16) for x in mac.split(":")]
    b[0] ^= 0x02
    iid = b[:3] + [0xFF, 0xFE] + b[3:]
    groups = [f"{iid[i] << 8 | iid[i + 1]:x}" for i in range(0, 8, 2)]
    return f"{prefix}:{':'.join(groups)}"


ANY4, ANY6 = net("0.0.0.0/0"), net("::/0")

# ---------------------------------------------------------------- modelo


@dataclass
class Iface:
    name: str
    segment: str | None
    addrs: list
    acl_in: str | None = None
    ospf: str | None = None  # 'active' | 'passive'
    up: bool = True


@dataclass
class Route:
    prefix: object
    kind: str  # C, S, O, O*E2
    iface: str
    nh: object = None
    ad: int = 0

    def __str__(self):
        via = f" via {self.nh}" if self.nh else ""
        return f"{self.kind:<4} {self.prefix}{via} [{self.iface}]"


@dataclass
class Pkt:
    src: object
    dst: object
    proto: str  # icmp | tcp | udp
    dport: int = 0
    sport: int = 40000
    icmp: str | None = None  # echo | echo-reply
    flags: str = "syn"  # syn = inicio de conexion, ack = establecida


class Node:
    kind = "router"

    def __init__(self, name, kind="router"):
        self.name, self.kind = name, kind
        self.ifaces, self.statics, self.rib = {}, [], []
        self.listen = set()
        self.ospf = False
        self.ospf_default = False
        self.nameservers = []
        self.dns = None
        self.vty_acl = None  # access-class de las lineas vty (solo routers)

    def iface(self, name, seg, *addrs, **kw):
        self.ifaces[name] = Iface(name, seg, [ipa.ip_interface(a) for a in addrs], **kw)
        return self

    def static(self, prefix, nh, iface=None, ad=1):
        """nh=None con iface='blackhole' crea una ruta de descarte."""
        self.statics.append((net(prefix), addr(nh) if nh else None, iface, ad))
        return self

    def addresses(self):
        for i in self.ifaces.values():
            if i.up:
                for a in i.addrs:
                    yield a.ip, i

    def owns(self, a):
        return any(x == a for x, _ in self.addresses())

    def source_for(self, dst):
        r = self.lookup(dst)
        cand = [a.ip for a in self.ifaces[r.iface].addrs] if r else []
        for a in cand:
            if a.version == dst.version and not a.is_link_local:
                return a
        raise ValueError(f"{self.name} sin direccion origen para {dst}")

    def lookup(self, dst):
        best = None
        for r in self.rib:
            if r.prefix.version == dst.version and dst in r.prefix:
                if best is None or r.prefix.prefixlen > best.prefix.prefixlen or (
                    r.prefix.prefixlen == best.prefix.prefixlen and r.ad < best.ad
                ):
                    best = r
        return best


@dataclass
class Ace:
    seq: int
    action: str
    proto: str = "ip"
    src: list | None = None
    dst: list | None = None
    dports: tuple | None = None
    icmp: str | None = None
    established: bool = False

    def matches(self, p):
        if self.proto != "ip" and self.proto != p.proto:
            return False
        if self.src and not any(p.src in n for n in self.src):
            return False
        if self.dst and not any(p.dst in n for n in self.dst):
            return False
        if self.dports and p.dport not in self.dports:
            return False
        if self.icmp and p.icmp != self.icmp:
            return False
        if self.established and p.flags == "syn":
            return False
        return True


class Acl:
    def __init__(self, name, v4, v6):
        self.name, self.rules, self.hits = name, {4: v4, 6: v6}, {}

    def eval(self, p):
        v = p.dst.version
        for r in self.rules[v]:
            if r.matches(p):
                self.hits[(v, r.seq)] = self.hits.get((v, r.seq), 0) + 1
                return r.action, r.seq
        self.hits[(v, "implicita")] = self.hits.get((v, "implicita"), 0) + 1
        return "deny", "implicita"


@dataclass
class Vip:
    name: str
    iface: str
    ext: object
    int: object


@dataclass
class Policy:
    id: int
    name: str
    src_if: str | tuple
    dst_if: str
    src: list
    dst: list
    svc: list
    action: str
    nat: bool = False
    enabled: bool = True
    hits: int = 0

    def __post_init__(self):
        if isinstance(self.src_if, str):
            self.src_if = (self.src_if,)


@dataclass
class Session:
    proto: str
    client: object
    sport: int
    dst_real: object
    dport: int
    snat: object
    orig_dst: object
    policy: int

    def is_reply(self, p):
        return (
            p.proto == self.proto
            and p.src == self.dst_real
            and p.sport == self.dport
            and p.dst == (self.snat or self.client)
            and p.dport == self.sport
        )


SERVICES = {
    "DNS": [("udp", 53), ("tcp", 53)],
    "HTTP": [("tcp", 80)],
    "HTTPS": [("tcp", 443)],
    "SSH": [("tcp", 22)],
    "PING": [("icmp", "echo")],
    "ALL": ["*"],
}


def svc_match(names, p):
    for n in names:
        for s in SERVICES[n]:
            if s == "*":
                return True
            if p.proto == "icmp" and s == ("icmp", p.icmp):
                return True
            if p.proto != "icmp" and s == (p.proto, p.dport):
                return True
    return False


def in_objs(a, objs):
    return any(isinstance(o, (ipa.IPv4Network, ipa.IPv6Network)) and a in o for o in objs)


class Fgt(Node):
    def __init__(self, name):
        super().__init__(name, "fgt")
        self.allow, self.trusted, self.vips, self.policies = {}, [], [], []
        self.sessions, self.logs, self.localin_denied = [], [], []
        self.central_nat = False
        self.listen = {("tcp", 443), ("tcp", 22)}

    def process(self, p, ing):
        for s in self.sessions:
            if s.is_reply(p):
                p = replace(p, src=s.orig_dst, dst=s.client)
                r = self.lookup(p.dst)
                return ("fwd", (p, r)) if r else ("drop", "sin ruta de retorno")
        if ing is None:  # trafico originado por el propio FortiGate
            r = self.lookup(p.dst)
            return ("fwd", (p, r)) if r else ("drop", "sin ruta")
        if self.owns(p.dst):
            return self.local_in(p, ing)
        vip, orig = None, p.dst
        for v in self.vips:
            if v.iface == ing.name and v.ext == p.dst:
                vip, p = v, replace(p, dst=v.int)
        r = self.lookup(p.dst)
        if not r:
            return "drop", f"FGT sin ruta hacia {p.dst}"
        if r.iface == "blackhole":
            return "drop", f"FGT descarta por ruta blackhole {r.prefix} (antes de evaluar politicas)"
        for pol in self.policies:
            if not pol.enabled or ing.name not in pol.src_if or pol.dst_if != r.iface:
                continue
            if not in_objs(p.src, pol.src):
                continue
            dst_ok = in_objs(p.dst, pol.dst) if (self.central_nat or not vip) else any(o is vip for o in pol.dst if isinstance(o, Vip))
            if not dst_ok or not svc_match(pol.svc, p):
                continue
            pol.hits += 1
            self.logs.append(dict(policy=pol.id, name=pol.name, action=pol.action, src=str(p.src),
                                  dst=str(orig), tran=str(p.dst) if vip else "-", proto=p.proto, dport=p.dport))
            if pol.action == "deny":
                return "drop", f"politica {pol.id} {pol.name} (deny)"
            snat = None
            if pol.nat and p.src.version == 4:
                snat = next(a.ip for a in self.ifaces[r.iface].addrs if a.version == 4)
            self.sessions.append(Session(p.proto, p.src, p.sport, p.dst, p.dport, snat, orig, pol.id))
            if snat:
                p = replace(p, src=snat)
            return "fwd", (p, r)
        self.logs.append(dict(policy=0, name="implicita", action="deny", src=str(p.src), dst=str(orig),
                              tran=str(p.dst) if vip else "-", proto=p.proto, dport=p.dport))
        return "drop", "politica implicita 0 (deny)"

    def local_in(self, p, ing):
        svc = {("tcp", 443): "https", ("tcp", 22): "ssh", ("tcp", 80): "http"}.get((p.proto, p.dport))
        if p.proto == "icmp" and p.icmp == "echo":
            svc = "ping"
        # localin_denied = log de Local Traffic (requiere activar el log de denegaciones local-in)
        if svc not in self.allow.get(ing.name, set()):
            self.localin_denied.append((str(p.src), str(p.dst), svc))
            return "drop", f"local-in: {ing.name} no tiene '{svc}' en allowaccess"
        if svc in ("https", "ssh") and not in_objs(p.src, self.trusted):
            self.localin_denied.append((str(p.src), str(p.dst), svc))
            return "drop", "local-in: origen fuera de trusted hosts"
        return "local", f"acceso {svc} al FortiGate aceptado"


@dataclass
class Result:
    ok: bool
    reason: str
    path: list
    pkt: Pkt | None = None
    dst_node: object = None


@dataclass
class Conv:
    ok: bool
    req: Result
    rep: Result | None
    note: str = ""

    def why(self):
        if not self.req.ok:
            return f"ida: {self.req.reason} | camino {'>'.join(self.req.path)}"
        if self.note:
            return self.note
        if self.rep and not self.rep.ok:
            return f"vuelta: {self.rep.reason} | camino {'>'.join(self.rep.path)}"
        return "ida y vuelta OK | " + ">".join(self.req.path)


class Network:
    def __init__(self):
        self.nodes, self.acls, self.adj = {}, {}, []
        self._sport = 40000

    def add(self, n):
        self.nodes[n.name] = n
        return n

    def __getitem__(self, k):
        return self.nodes[k]

    def on_segment(self, seg):
        return [(n, i) for n in self.nodes.values() for i in n.ifaces.values() if i.segment == seg and i.up]

    def arp(self, seg, ip):
        for n, i in self.on_segment(seg):
            if any(a.ip == ip for a in i.addrs):
                return n, i
            if isinstance(n, Fgt) and any(v.iface == i.name and v.ext == ip for v in n.vips):
                return n, i
        return None

    def build_ribs(self):
        self.adj = []
        for n in self.nodes.values():
            n.rib = []
            for i in n.ifaces.values():
                if i.up:
                    for a in i.addrs:
                        if not a.ip.is_link_local:
                            n.rib.append(Route(a.network, "C", i.name))
            for pfx, nh, ifn, ad in n.statics:
                if ifn == "blackhole":
                    n.rib.append(Route(pfx, "S", "blackhole", None, ad))
                    continue
                if ifn is None:
                    c = next((r for r in n.rib if r.kind == "C" and nh in r.prefix), None)
                    if not c:
                        continue
                    ifn = c.iface
                elif not n.ifaces[ifn].up:
                    continue
                n.rib.append(Route(pfx, "S", ifn, nh, ad))
        for n in self.nodes.values():
            if not n.ospf:
                continue
            for i in n.ifaces.values():
                if not (i.up and i.ospf == "active"):
                    continue
                for m, j in self.on_segment(i.segment):
                    if m is n or not m.ospf or j.ospf != "active":
                        continue
                    nh = {a.version: a.ip for a in j.addrs if not a.ip.is_link_local}
                    nh[6] = next(a.ip for a in j.addrs if a.ip.is_link_local)
                    self.adj.append((n.name, i.name, m.name, j.name, nh[4], nh[6]))
                    have = {r.prefix for r in n.rib if r.kind == "C"}
                    for k in m.ifaces.values():
                        if k.up and k.ospf:
                            for a in k.addrs:
                                if not a.ip.is_link_local and a.network not in have:
                                    n.rib.append(Route(a.network, "O", i.name, nh[a.version], 110))
                    if m.ospf_default:
                        for d in (ANY4, ANY6):
                            if any(s[0] == d for s in m.statics):
                                n.rib.append(Route(d, "O*E2", i.name, nh[d.version], 110))

    def send(self, p, src_node):
        path, cur, ing = [], src_node, None
        for _ in range(32):
            path.append(cur.name)
            if ing and ing.acl_in:
                act, seq = self.acls[ing.acl_in].eval(p)
                if act == "deny":
                    return Result(False, f"{ing.acl_in} linea {seq} en {cur.name} {ing.name} (in)", path)
            if isinstance(cur, Fgt):
                st, info = cur.process(p, ing)
                if st == "drop":
                    return Result(False, info, path)
                if st == "local":
                    return Result(True, info, path, p, cur)
                p, route = info
            else:
                if cur.owns(p.dst):
                    if cur.vty_acl and p.proto == "tcp" and p.dport in (22, 23) and p.flags == "syn":
                        act, seq = self.acls[cur.vty_acl].eval(p)
                        if act == "deny":
                            return Result(False, f"{cur.vty_acl} linea {seq} (access-class vty de {cur.name})", path)
                    return Result(True, "entregado", path, p, cur)
                if ing is not None and cur.kind == "host":
                    return Result(False, f"{cur.name} es host y no reenvia", path)
                route = cur.lookup(p.dst)
                if not route:
                    return Result(False, f"sin ruta hacia {p.dst} en {cur.name}", path)
            if route.iface == "blackhole":
                return Result(False, f"{cur.name} descarta por blackhole {route.prefix}", path)
            nh = route.nh or p.dst
            out = cur.ifaces[route.iface]
            nb = self.arp(out.segment, nh) if out.segment else None
            if not nb:
                return Result(False, f"{cur.name}: nadie responde ARP/ND por {nh} en {out.name}", path)
            cur, ing = nb
        return Result(False, "TTL agotado (bucle de enrutamiento)", path)

    def converse(self, src_node, dst, proto, dport=0, src=None, flags="syn"):
        node = self[src_node] if isinstance(src_node, str) else src_node
        dst = addr(dst) if isinstance(dst, str) else dst
        src = addr(src) if isinstance(src, str) else (src or node.source_for(dst))
        self._sport += 1
        p = Pkt(src, dst, proto, dport, self._sport, "echo" if proto == "icmp" else None, flags)
        r = self.send(p, node)
        if not r.ok:
            return Conv(False, r, None)
        dn, arrived = r.dst_node, r.pkt
        app_ok = proto == "icmp" or (proto, dport) in dn.listen
        if not app_ok and proto == "udp":
            return Conv(False, r, None, f"llego a {dn.name} pero el puerto UDP {dport} esta cerrado")
        rep = Pkt(arrived.dst, arrived.src, proto, arrived.sport, arrived.dport,
                  "echo-reply" if proto == "icmp" else None, "ack")
        rr = self.send(rep, dn)
        ok = rr.ok and rr.dst_node is node
        if ok and not app_ok:
            return Conv(False, r, rr, f"llego a {dn.name} pero TCP {dport} cerrado (RST)")
        return Conv(ok, r, rr)

    def resolve(self, client, name, qtype, server=None):
        node = self[client]
        servers = [addr(server)] if server else node.nameservers
        fails = []
        for ns in servers:
            c = self.converse(node, ns, "udp", 53)
            if c.ok:
                srv = c.req.dst_node
                view, ans = srv.dns.answer(c.req.pkt.src, name, qtype)
                return dict(ok=bool(ans), ns=ns, view=view, answer=ans, conv=c)
            fails.append(f"{ns}: {c.why()}")
        return dict(ok=False, ns=None, view=None, answer=None, fails=fails)

    def curl(self, client, name, family):
        res = self.resolve(client, name, "A" if family == 4 else "AAAA")
        if not res["ok"]:
            return False, f"no resuelve: {res.get('fails') or res}"
        c = self.converse(client, res["answer"], "tcp", 80)
        return c.ok, f"{name} -> {res['answer']} (vista {res['view']}, NS {res['ns']}) ; HTTP: {c.why()}"


class DnsServer:
    def __init__(self, views):
        # [(nombre, [redes incluidas] | None, [redes excluidas], {(fqdn, tipo): valor})]
        self.views = views

    def answer(self, client_ip, name, qtype):
        for vname, match, exclude, recs in self.views:
            if in_objs(client_ip, exclude):
                continue
            if match is None or in_objs(client_ip, match):
                return vname, recs.get((name, qtype))
        return None, None


# ---------------------------------------------------------------- topologia del documento

ZONE = "g5.eif101o.test"
MAC_PC_USER = "0c:7a:15:00:00:10"
SLAAC_PC_USER = eui64("2001:db8:105:10", MAC_PC_USER)

NET_USUARIOS = [net("10.50.0.0/24"), net("2001:db8:105:10::/64")]
NET_ADMIN = [net("10.50.1.0/27"), net("2001:db8:105:20::/64")]
NET_LAN = NET_USUARIOS + NET_ADMIN
SRV_V6 = [net("2001:db8:105:30::10/128")]
SRV = [net("10.50.1.34/32")] + SRV_V6
ALL = [ANY4, ANY6]


def build(plan_b=False):
    """plan_b=True arma el FortiGate reducido para la licencia de prueba (3 politicas)."""
    N = Network()

    risp = N.add(Node("R-ISP"))
    risp.iface("Gi0/0", "isp", "203.0.113.1/30", "2001:db8:ffff:1::1/64", "fe80::1/64")
    risp.iface("Gi0/1", "extA", "198.51.100.1/24", "2001:db8:ffff:100::1/64", "fe80::1/64")
    risp.iface("Gi0/2", "extB", "192.0.2.1/24", "2001:db8:ffff:200::1/64", "fe80::1/64")
    risp.static("203.0.113.16/29", "203.0.113.2").static("2001:db8:105::/48", "2001:db8:ffff:1::2")
    risp.listen = {("tcp", 22)}

    redge = N.add(Node("R-EDGE"))
    redge.iface("Gi0/0", "isp", "203.0.113.2/30", "2001:db8:ffff:1::2/64", "fe80::2/64", acl_in="ACL-BORDE-IN")
    redge.iface("Gi0/1", "wan", "203.0.113.17/29", "2001:db8:105:ff01::1/64", "fe80::1/64")
    redge.static("0.0.0.0/0", "203.0.113.1").static("::/0", "2001:db8:ffff:1::1")
    redge.static("2001:db8:105::/48", "2001:db8:105:ff01::2")
    redge.listen = {("tcp", 22)}
    redge.vty_acl = "ACL-VTY-NINGUNO"

    fgt = N.add(Fgt("FGT-01"))
    fgt.iface("port1", "wan", "203.0.113.18/29", "2001:db8:105:ff01::2/64", "fe80::f1/64")
    fgt.iface("port2", "transit", "10.50.1.49/30", "2001:db8:105:ff00::1/64", "fe80::f2/64", ospf="active")
    fgt.iface("port3", "dmz", "10.50.1.33/28", "2001:db8:105:30::1/64", "fe80::f3/64", ospf="passive")
    fgt.static("0.0.0.0/0", "203.0.113.17", ad=10).static("::/0", "2001:db8:105:ff01::1", ad=10)
    fgt.static("10.50.0.0/16", None, "blackhole", ad=254)
    fgt.static("2001:db8:105::/48", None, "blackhole", ad=254)
    fgt.ospf = fgt.ospf_default = True
    fgt.allow = {"port1": {"ping"}, "port2": {"https", "ssh", "ping"}, "port3": {"ping"}}
    fgt.trusted = NET_ADMIN
    vip = Vip("VIP-SRV-DMZ", "port1", addr("203.0.113.20"), addr("10.50.1.34"))
    fgt.vips = [vip]
    fgt.policies = [
        Policy(1, "PUB-DNS-HTTP", "port1", "port3", ALL, [vip] + SRV_V6, ["DNS", "HTTP"], "accept"),
        Policy(2, "ADMIN-A-DMZ", "port2", "port3", NET_ADMIN, SRV, ["SSH", "DNS", "HTTP", "PING"], "accept"),
        Policy(3, "USUARIOS-A-DMZ", "port2", "port3", NET_USUARIOS, SRV, ["DNS", "HTTP"], "accept"),
        Policy(4, "LAN-A-INTERNET", "port2", "port1", NET_LAN, ALL, ["HTTP", "HTTPS", "DNS", "PING"], "accept", nat=True),
        Policy(5, "DENY-EXT-A-LAN", "port1", "port2", ALL, ALL, ["ALL"], "deny"),
        Policy(6, "DENY-DMZ-A-LAN", "port3", "port2", ALL, ALL, ["ALL"], "deny"),
    ]
    if plan_b:
        fgt.central_nat = True
        fgt.policies = [
            Policy(1, "DNS-HTTP-A-DMZ", ("port1", "port2"), "port3", ALL, SRV, ["DNS", "HTTP"], "accept"),
            fgt.policies[1],
            Policy(3, "DENY-A-LAN", ("port1", "port3"), "port2", ALL, ALL, ["ALL"], "deny"),
        ]

    rlan = N.add(Node("R-LAN"))
    rlan.iface("Gi0/0", "transit", "10.50.1.50/30", "2001:db8:105:ff00::2/64", "fe80::2/64", ospf="active")
    rlan.iface("Gi0/1.10", "vlan10", "10.50.0.1/24", "2001:db8:105:10::1/64", "fe80::1/64",
               ospf="passive", acl_in="ACL-SEG-USUARIOS")
    rlan.iface("Gi0/1.20", "vlan20", "10.50.1.1/27", "2001:db8:105:20::1/64", "fe80::1/64", ospf="passive")
    rlan.ospf = True
    rlan.listen = {("tcp", 22)}
    rlan.vty_acl = "ACL-VTY-ADMIN"

    def host(name, seg, v4, v6, ll, gw4, gw6, gw6_if=None):
        h = N.add(Node(name, "host"))
        h.iface("eth0", seg, v4, v6, ll)
        h.static("0.0.0.0/0", gw4).static("::/0", gw6, gw6_if)
        return h

    srv = host("SRV-DMZ", "dmz", "10.50.1.34/28", "2001:db8:105:30::10/64", "fe80::10/64",
               "10.50.1.33", "2001:db8:105:30::1")
    srv.listen = {("udp", 53), ("tcp", 53), ("tcp", 80), ("tcp", 22)}
    v6 = "2001:db8:105:30::10"
    common = {(f"{ZONE}.", "NS"): f"ns1.{ZONE}.", (f"ns1.{ZONE}", "AAAA"): v6,
              (f"www.{ZONE}", "AAAA"): v6, (f"v6.{ZONE}", "AAAA"): v6}

    def a_records(ip4):
        return {(f"{h}.{ZONE}", "A"): ip4 for h in ("ns1", "www", "v4")}

    srv.dns = DnsServer([
        ("interna", [net("10.50.0.0/16"), net("2001:db8:105::/48")], [net("2001:db8:105:ff01::/64")],
         {**common, **a_records("10.50.1.34")}),
        ("externa", None, [], {**common, **a_records("203.0.113.20")}),
    ])
    srv.nameservers = [addr("10.50.1.34")]

    ext_ns = [addr("203.0.113.20"), addr("2001:db8:105:30::10")]
    lan_ns = [addr("10.50.1.34"), addr("2001:db8:105:30::10")]
    host("PC-EXT", "extA", "198.51.100.10/24", "2001:db8:ffff:100::10/64", "fe80::10/64",
         "198.51.100.1", "fe80::1", "eth0").nameservers = ext_ns
    host("PC-EXT-WEB", "extB", "192.0.2.10/24", "2001:db8:ffff:200::10/64", "fe80::10/64",
         "192.0.2.1", "fe80::1", "eth0").nameservers = ext_ns
    host("PC-USER", "vlan10", "10.50.0.10/24", SLAAC_PC_USER + "/64",
         eui64("fe80:0:0:0", MAC_PC_USER) + "/64", "10.50.0.1", "fe80::1", "eth0").nameservers = lan_ns
    adm = host("PC-ADMIN", "vlan20", "10.50.1.10/27", "2001:db8:105:20::10/64", "fe80::10/64",
               "10.50.1.1", "fe80::1", "eth0")
    adm.nameservers = lan_ns
    adm.listen = {("udp", 514)}  # syslog

    users4, admin4 = NET_USUARIOS[0], NET_ADMIN[0]
    users6, admin6 = NET_USUARIOS[1], NET_ADMIN[1]
    seg4 = [Ace(10, "permit", "icmp", [users4], [admin4], icmp="echo-reply"),
            Ace(20, "permit", "tcp", [users4], [admin4], established=True),
            Ace(30, "deny", "ip", [users4], [admin4])]
    seg6 = [Ace(10, "permit", "icmp", [users6], [admin6], icmp="echo-reply"),
            Ace(20, "permit", "tcp", [users6], [admin6], established=True),
            Ace(30, "deny", "ip", [users6], [admin6])]
    N.acls["ACL-SEG-USUARIOS"] = Acl("ACL-SEG-USUARIOS", seg4 + [Ace(40, "permit")], seg6 + [Ace(40, "permit")])
    N.acls["ACL-VTY-ADMIN"] = Acl("ACL-VTY-ADMIN",
        [Ace(10, "permit", src=[admin4]), Ace(20, "deny")],
        [Ace(10, "permit", src=[admin6]), Ace(20, "deny")])
    N.acls["ACL-VTY-NINGUNO"] = Acl("ACL-VTY-NINGUNO", [Ace(10, "deny")], [Ace(10, "deny")])
    N.acls["ACL-BORDE-IN"] = Acl("ACL-BORDE-IN",
        [Ace(10, "deny", src=[net(x) for x in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8")]),
         Ace(20, "deny", src=[net("203.0.113.16/29")]),
         Ace(30, "deny", "tcp", dst=[net("203.0.113.2/32"), net("203.0.113.17/32")], dports=(22, 23)),
         Ace(40, "permit")],
        [Ace(10, "deny", src=[net("2001:db8:105::/48"), net("fc00::/7")]),
         Ace(30, "deny", "tcp", dst=[net("2001:db8:ffff:1::2/128"), net("2001:db8:105:ff01::1/128")], dports=(22, 23)),
         Ace(40, "permit")])

    N.build_ribs()
    return N


# ---------------------------------------------------------------- pruebas

WWW, V4, V6 = f"www.{ZONE}", f"v4.{ZONE}", f"v6.{ZONE}"

EXPECTED_RIB = {
    "R-LAN": {"C 10.50.0.0/24", "C 10.50.1.0/27", "C 10.50.1.48/30", "O 10.50.1.32/28", "O*E2 0.0.0.0/0",
              "C 2001:db8:105:10::/64", "C 2001:db8:105:20::/64", "C 2001:db8:105:ff00::/64",
              "O 2001:db8:105:30::/64", "O*E2 ::/0"},
    "FGT-01": {"S 0.0.0.0/0", "S 10.50.0.0/16", "C 203.0.113.16/29", "C 10.50.1.48/30", "C 10.50.1.32/28",
               "O 10.50.0.0/24", "O 10.50.1.0/27", "S ::/0", "S 2001:db8:105::/48", "C 2001:db8:105:ff01::/64",
               "C 2001:db8:105:ff00::/64", "C 2001:db8:105:30::/64", "O 2001:db8:105:10::/64",
               "O 2001:db8:105:20::/64"},
    "R-EDGE": {"S 0.0.0.0/0", "C 203.0.113.0/30", "C 203.0.113.16/29", "S ::/0", "S 2001:db8:105::/48",
               "C 2001:db8:ffff:1::/64", "C 2001:db8:105:ff01::/64"},
    "R-ISP": {"C 203.0.113.0/30", "C 198.51.100.0/24", "C 192.0.2.0/24", "S 203.0.113.16/29",
              "C 2001:db8:ffff:1::/64", "C 2001:db8:ffff:100::/64", "C 2001:db8:ffff:200::/64",
              "S 2001:db8:105::/48"},
}


class Report:
    def __init__(self):
        self.rows = []

    def check(self, tid, desc, ok, detail):
        self.rows.append((tid, bool(ok), desc, detail))
        return bool(ok)

    def print(self, title):
        print(f"\n== {title} ==")
        for tid, ok, desc, det in self.rows:
            print(f"[{'OK   ' if ok else 'FALLA'}] {tid}  {desc}\n          {det}")
        passed = sum(1 for r in self.rows if r[1])
        print(f"\nResultado: {passed}/{len(self.rows)} verificaciones OK")
        return passed == len(self.rows)


def new_logs(N, mark):
    return N["FGT-01"].logs[mark:]


def pols(logs):
    return sorted({l["policy"] for l in logs})


def syslog(N, sender, dst="10.50.1.10"):
    """Envia un mensaje syslog (UDP 514, sin respuesta) y dice si llego a PC-ADMIN."""
    node, dst = N[sender], addr(dst)
    r = N.send(Pkt(node.source_for(dst), dst, "udp", 514), node)
    return r.ok and r.dst_node is N["PC-ADMIN"], r


def run_matrix(N, rep):
    fgt = N["FGT-01"]
    chk = rep.check

    # --- P: minimas del enunciado
    r = N.resolve("PC-EXT", WWW, "A")
    chk("P01", "Resolucion A desde PC-EXT", r["answer"] == "203.0.113.20", f"{WWW} A -> {r['answer']} (vista {r['view']})")
    r = N.resolve("PC-EXT", WWW, "AAAA")
    chk("P02", "Resolucion AAAA desde PC-EXT", r["answer"] == "2001:db8:105:30::10", f"{WWW} AAAA -> {r['answer']}")
    m = len(fgt.logs)
    r = N.resolve("PC-EXT", WWW, "A", server="203.0.113.20")
    lg = new_logs(N, m)
    chk("P03", "Consulta DNS por transporte IPv4 (al VIP)", r["ok"] and pols(lg) == [1],
        f"respuesta={r['answer']}, log={pols(lg)}, traduccion {lg[0]['dst']}->{lg[0]['tran']}" if lg else str(r))
    m = len(fgt.logs)
    r = N.resolve("PC-EXT", WWW, "AAAA", server="2001:db8:105:30::10")
    lg = new_logs(N, m)
    chk("P04", "Consulta DNS por transporte IPv6", r["ok"] and pols(lg) == [1], f"respuesta={r['answer']}, log={pols(lg)}")

    ok, d = N.curl("PC-EXT", WWW, 4)
    p05 = chk("P05", "HTTP IPv4 por nombre: curl -4 www desde PC-EXT", ok, d)
    only_a = N.resolve("PC-EXT-WEB", V4, "AAAA")["answer"] is None
    ok, d = N.curl("PC-EXT-WEB", V4, 4)
    p05 &= chk("P05", "HTTP IPv4 por nombre: navegador a v4 (solo A) desde PC-EXT-WEB", ok and only_a,
               f"v4 sin AAAA={only_a} ; {d}")
    ok, d = N.curl("PC-EXT", WWW, 6)
    chk("P06", "HTTP IPv6 por nombre: curl -6 www desde PC-EXT", ok, d)
    only_aaaa = N.resolve("PC-EXT-WEB", V6, "A")["answer"] is None
    ok, d = N.curl("PC-EXT-WEB", V6, 6)
    chk("P06", "HTTP IPv6 por nombre: navegador a v6 (solo AAAA) desde PC-EXT-WEB", ok and only_aaaa,
        f"v6 sin A={only_aaaa} ; {d}")

    # --- E: especificas del caso
    m = len(fgt.logs)
    c = N.converse("PC-EXT", SLAAC_PC_USER, "icmp")
    lg = new_logs(N, m)
    e01 = chk("E01", "Externo -> LAN por IPv6 (PC-USER SLAAC)", not c.ok and pols(lg) == [5], f"{c.why()} ; log={pols(lg)}")
    chk("P07", "Politica permitida y denegada", p05 and e01, "se cumple con P05 (politica 1) + E01 (politica 5)")
    c = N.converse("PC-EXT", "10.50.0.10", "icmp")
    chk("E02", "Externo -> LAN por IPv4", not c.ok and "R-ISP" in c.req.reason, c.why())

    N2 = build()
    N2["R-ISP"].static("10.50.0.0/16", "203.0.113.2")
    N2["R-EDGE"].static("10.50.0.0/16", "203.0.113.18")
    N2.build_ribs()
    m = len(N2["FGT-01"].logs)
    c = N2.converse("PC-EXT", "10.50.0.10", "icmp")
    lg = new_logs(N2, m)
    chk("E02b", "Externo -> LAN por IPv4 con ruta filtrada", not c.ok and pols(lg) == [5], f"{c.why()} ; log={pols(lg)}")

    m = len(fgt.logs)
    c4 = N.converse("PC-EXT", "203.0.113.20", "tcp", 22)
    c6 = N.converse("PC-EXT", "2001:db8:105:30::10", "tcp", 22)
    lg = new_logs(N, m)
    chk("E03", "SSH externo al servidor (v4 VIP y v6)", not c4.ok and not c6.ok and pols(lg) == [0],
        f"v4: {c4.why()} ; v6: {c6.why()} ; log={pols(lg)}")
    m = len(fgt.logs)
    c4 = N.converse("PC-ADMIN", "10.50.1.34", "tcp", 22)
    c6 = N.converse("PC-ADMIN", "2001:db8:105:30::10", "tcp", 22)
    lg = new_logs(N, m)
    chk("E04", "Admin SSH al servidor (v4 y v6)", c4.ok and c6.ok and pols(lg) == [2], f"{c4.why()} ; log={pols(lg)}")
    m = len(fgt.logs)
    c = N.converse("PC-USER", "10.50.1.34", "tcp", 22)
    lg = new_logs(N, m)
    chk("E05", "Usuario SSH al servidor", not c.ok and pols(lg) == [0], f"{c.why()} ; log={pols(lg)}")
    m = len(fgt.logs)
    ra, raaaa = N.resolve("PC-USER", WWW, "A"), N.resolve("PC-USER", WWW, "AAAA")
    h4, _ = N.curl("PC-USER", WWW, 4)
    h6, _ = N.curl("PC-USER", WWW, 6)
    lg = new_logs(N, m)
    chk("E06", "Usuario consume DNS y HTTP (vista interna)",
        ra["answer"] == "10.50.1.34" and raaaa["ok"] and h4 and h6 and pols(lg) == [3],
        f"A={ra['answer']} AAAA={raaaa['answer']} http4={h4} http6={h6} log={pols(lg)}")
    c4 = N.converse("PC-USER", "10.50.1.10", "icmp")
    c6 = N.converse("PC-USER", "2001:db8:105:20::10", "tcp", 22)
    chk("E07", "Usuarios -> Admin bloqueado", not c4.ok and not c6.ok and "linea 30" in c4.req.reason,
        f"v4 ping: {c4.why()} ; v6 ssh: {c6.why()}")
    c = N.converse("PC-ADMIN", "10.50.0.10", "icmp")
    hits10 = N.acls["ACL-SEG-USUARIOS"].hits.get((4, 10), 0)
    chk("E08", "Admin -> Usuarios ping (respuesta por linea 10)", c.ok and hits10 > 0, f"{c.why()} ; contador linea 10 = {hits10}")
    m = len(fgt.logs)
    c = N.converse("SRV-DMZ", "10.50.0.10", "icmp")
    lg = new_logs(N, m)
    chk("E09", "DMZ -> LAN bloqueado", not c.ok and pols(lg) == [6], f"{c.why()} ; log={pols(lg)}")
    N["R-ISP"].iface("Lo99", None, "10.99.99.99/32")
    c = N.converse("R-ISP", "203.0.113.20", "icmp", src="10.99.99.99")
    del N["R-ISP"].ifaces["Lo99"]
    chk("E10", "Origen falsificado 10.99.99.99 en el borde", not c.ok and "ACL-BORDE-IN linea 10" in c.req.reason, c.why())
    m = len(fgt.localin_denied)
    c = N.converse("PC-EXT", "203.0.113.18", "tcp", 443)
    li = fgt.localin_denied[m:]
    chk("E11", "Gestion HTTPS del FortiGate desde WAN", not c.ok and li, f"{c.why()} ; log local-in={li}")

    u4 = N.converse("PC-USER", "10.50.0.1", "tcp", 22)
    u6 = N.converse("PC-USER", "2001:db8:105:ff00::2", "tcp", 22)
    a4 = N.converse("PC-ADMIN", "10.50.1.1", "tcp", 22)
    a6 = N.converse("PC-ADMIN", "2001:db8:105:20::1", "tcp", 22)
    chk("E12", "Gestion de R-LAN: bloqueada a Usuarios, permitida a Admin",
        not u4.ok and not u6.ok and a4.ok and a6.ok and "ACL-VTY-ADMIN linea 20" in u4.req.reason,
        f"PC-USER v4: {u4.why()} ; PC-USER v6: {u6.req.reason} ; PC-ADMIN v4/v6: {a4.ok}/{a6.ok}")
    m = len(fgt.localin_denied)
    u = N.converse("PC-USER", "10.50.1.49", "tcp", 443)
    a = N.converse("PC-ADMIN", "10.50.1.49", "tcp", 443)
    li = fgt.localin_denied[m:]
    chk("E13", "GUI del FortiGate: sin respuesta a Usuarios, OK para Admin", not u.ok and a.ok and li,
        f"PC-USER: {u.why()} ; PC-ADMIN: {a.ok} ; log local-in={li}")
    m = len(fgt.logs)
    c = N.converse("SRV-DMZ", "198.51.100.10", "icmp")
    lg = new_logs(N, m)
    chk("E14", "SRV-DMZ no puede iniciar trafico a Internet", not c.ok and pols(lg) == [0], f"{c.why()} ; log={pols(lg)}")
    m = len(fgt.logs)
    c4 = N.converse("PC-USER", "10.50.99.9", "icmp")
    c6 = N.converse("PC-USER", "2001:db8:105:99::9", "icmp")
    lg = new_logs(N, m)
    chk("E15", "Destino interno inexistente descartado en el FGT",
        not c4.ok and not c6.ok and "blackhole" in c4.req.reason and "blackhole" in c6.req.reason and 4 not in pols(lg),
        f"v4: {c4.why()} ; v6: {c6.req.reason} ; log={pols(lg)}")
    f_ok, fr = syslog(N, "FGT-01")
    r_ok, rr = syslog(N, "R-LAN")
    chk("E16", "Syslog del FGT y de R-LAN llega a PC-ADMIN", f_ok and r_ok,
        f"FGT: {'>'.join(fr.path)} ({fr.reason}) ; R-LAN: {'>'.join(rr.path)} ({rr.reason})")

    # --- R: enrutamiento
    chk("R01", "Vecindad OSPF FGT-01 <-> R-LAN", len(N.adj) == 2,
        "; ".join(f"{a} {b} -> {c} {d}: v2 nh {e}, v3 nh {f}" for a, b, c, d, e, f in N.adj))
    for name, exp in EXPECTED_RIB.items():
        got = {f"{r.kind} {r.prefix}" for r in N[name].rib}
        miss, extra = exp - got, got - exp
        chk("R02", f"Tabla de rutas {name} coincide con el documento", not miss and not extra,
            f"faltan={sorted(miss)} sobran={sorted(extra)}" if miss or extra else f"{len(got)} rutas OK")


def run_failures(rep):
    chk = rep.check
    # F01: desactivar politica 1
    N = build()
    fgt = N["FGT-01"]
    pol1 = next(p for p in fgt.policies if p.id == 1)
    pol1.enabled = False
    m = len(fgt.logs)
    ok4, _ = N.curl("PC-EXT", WWW, 4)
    r = N.resolve("PC-EXT", WWW, "A", server="203.0.113.20")
    lg = new_logs(N, m)
    chk("F01", "Politica 1 desactivada: publicacion cae", not ok4 and not r["ok"] and set(pols(lg)) == {0},
        f"http4={ok4}, dns={r['ok']}, log={pols(lg)}")
    pol1.enabled = True
    ok4, _ = N.curl("PC-EXT", WWW, 4)
    chk("F01", "Politica 1 reactivada: publicacion vuelve", ok4, f"http4={ok4}")

    # F02: apagar R-LAN Gi0/0 (el lado del FGT sigue up, como en GNS3)
    N = build()
    N["R-LAN"].ifaces["Gi0/0"].up = False
    N.build_ribs()
    u, du = N.curl("PC-USER", WWW, 4)
    e, _ = N.curl("PC-EXT", WWW, 4)
    chk("F02", "R-LAN Gi0/0 caido: LAN pierde servicio, externo sigue", not u and e and not N.adj,
        f"PC-USER: {du} || PC-EXT http4={e} || adyacencias={len(N.adj)}")
    N["R-LAN"].ifaces["Gi0/0"].up = True
    N.build_ribs()
    u, _ = N.curl("PC-USER", WWW, 4)
    chk("F02", "R-LAN Gi0/0 restaurado: vuelve", u and len(N.adj) == 2, f"PC-USER http4={u}")


def run_plan_b(rep):
    """FortiGate reducido para la licencia de prueba: politicas 1 (DNS y HTTP desde WAN y LAN), 2 (admin) y 3 (deniega WAN y DMZ hacia la LAN)."""
    chk = rep.check
    N = build(plan_b=True)
    fgt = N["FGT-01"]
    chk("B00", "Cabe en el limite medido de la licencia de prueba (3 politicas)",
        len(fgt.policies) <= 3 and len(fgt.ifaces) <= 3,
        f"politicas={[p.id for p in fgt.policies]}, rutas estaticas={len(fgt.statics)}, interfaces={len(fgt.ifaces)}")
    ok4, d4 = N.curl("PC-EXT", WWW, 4)
    ok6, _ = N.curl("PC-EXT", WWW, 6)
    chk("P05/P06", "Publicacion desde afuera, IPv4 e IPv6", ok4 and ok6, d4)
    m = len(fgt.logs)
    c = N.converse("PC-EXT", SLAAC_PC_USER, "icmp")
    chk("E01", "Externo -> LAN por IPv6 (politica 3)", not c.ok and pols(new_logs(N, m)) == [3], c.why())
    m = len(fgt.logs)
    c = N.converse("PC-EXT", "203.0.113.20", "tcp", 22)
    chk("E03", "SSH externo al servidor", not c.ok and pols(new_logs(N, m)) == [0], c.why())
    m = len(fgt.logs)
    c = N.converse("PC-ADMIN", "10.50.1.34", "tcp", 22)
    chk("E04", "Admin SSH al servidor", c.ok and pols(new_logs(N, m)) == [2], c.why())
    m = len(fgt.logs)
    c4 = N.converse("PC-USER", "10.50.1.34", "tcp", 22)
    c6 = N.converse("PC-USER", "2001:db8:105:30::10", "tcp", 22)
    chk("E05", "Usuario SSH al servidor (denegacion implicita)", not c4.ok and not c6.ok and pols(new_logs(N, m)) == [0],
        f"v4: {c4.why()} ; v6: {c6.why()}")
    m = len(fgt.logs)
    h4, _ = N.curl("PC-USER", WWW, 4)
    h6, _ = N.curl("PC-USER", WWW, 6)
    chk("E06", "Usuario consume DNS y HTTP (politica 1)", h4 and h6 and pols(new_logs(N, m)) == [1],
        f"http4={h4} http6={h6}")
    c = N.converse("PC-USER", "10.50.1.10", "icmp")
    chk("E07", "Usuarios -> Admin bloqueado", not c.ok and "linea 30" in c.req.reason, c.why())
    m = len(fgt.logs)
    c = N.converse("SRV-DMZ", "10.50.0.10", "icmp")
    chk("E09", "DMZ -> LAN (politica 3)", not c.ok and pols(new_logs(N, m)) == [3], c.why())
    m = len(fgt.logs)
    c = N.converse("SRV-DMZ", "198.51.100.10", "icmp")
    chk("E14", "SRV-DMZ -> Internet (denegacion implicita)", not c.ok and pols(new_logs(N, m)) == [0], c.why())
    m = len(fgt.logs)
    c4 = N.converse("PC-USER", "10.50.99.9", "icmp")
    c6 = N.converse("PC-USER", "2001:db8:105:99::9", "icmp")
    lg = new_logs(N, m)
    chk("E15", "Destino interno inexistente descartado por la blackhole",
        not c4.ok and not c6.ok and "blackhole" in c4.req.reason and "blackhole" in c6.req.reason and not lg,
        f"v4: {c4.why()} ; v6: {c6.req.reason}")


def run_design(rep):
    """Verificaciones de diseno sin ID en la matriz (comportamientos documentados)."""
    chk = rep.check
    N = build()
    view, ans = N["SRV-DMZ"].dns.answer(addr("2001:db8:105:ff01::1"), WWW, "A")
    chk("D01", "Consulta desde la WAN ff01::/64 recibe la vista externa", view == "externa", f"vista {view}: www A -> {ans}")
    c = N.converse("PC-USER", "10.50.1.10", "tcp", 22, flags="ack")
    chk("D02", "Limitacion documentada: ACK forjado pasa la linea 20 (el host lo descarta)",
        c.req.ok, f"la ACL lo dejo llegar hasta {c.req.path[-1]}")
    ok, r = syslog(N, "R-EDGE")
    chk("D03", "R-EDGE no puede mandar syslog a la LAN (por diseno: solo buffer local)", not ok, r.reason)
    c = N.converse("PC-ADMIN", "203.0.113.17", "tcp", 22)
    chk("D04", "R-EDGE no es gestionable por SSH desde la LAN (solo consola)", not c.ok, c.why())


def main():
    N = build()
    print(f"SLAAC simulada de PC-USER (EUI-64, MAC {MAC_PC_USER}): {SLAAC_PC_USER}\n")
    print("== Tablas de rutas simuladas ==")
    for name in ("R-ISP", "R-EDGE", "FGT-01", "R-LAN"):
        print(f"-- {name}")
        for r in sorted(N[name].rib, key=lambda r: (r.prefix.version, str(r.prefix))):
            print("   ", r)

    main_rep = Report()
    run_matrix(N, main_rep)
    run_failures(main_rep)
    ok = main_rep.print("Matriz de pruebas del documento (diseno normal)")

    print("\n== Logs del FortiGate (corrida principal) ==")
    for l in N["FGT-01"].logs:
        print(f"   pol={l['policy']:<2} {l['action']:<6} {l['proto']:<4} {l['src']:>32} -> {l['dst']:<32}"
              f" dport={l['dport']:<3} tran={l['tran']}")
    print("   Local Traffic (local-in denegado):", N["FGT-01"].localin_denied)
    print("\n== Contadores de ACL ==")
    for a in N.acls.values():
        print(f"   {a.name}: {a.hits}")

    b = Report()
    run_plan_b(b)
    ok &= b.print("Plan B (licencia de prueba)")
    d = Report()
    run_design(d)
    ok &= d.print("Verificaciones de diseno")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
