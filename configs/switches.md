# Switches

Fuente: sección Cableado de `docs/especificacion.md`. El diseño usa el **Ethernet switch integrado de GNS3**, que no tiene CLI: se configura desde la interfaz gráfica.

## Ethernet switch de GNS3 (diseño actual)

Clic derecho sobre el switch → **Configure**. Para cada puerto se elige el número, la VLAN y el tipo, y se pulsa **Add**. En un puerto `dot1q`, el campo VLAN es la VLAN nativa (sin etiqueta); las demás pasan etiquetadas.

### SW-LAN

| Puerto | VLAN | Tipo | Conecta a |
| --- | --- | --- | --- |
| 0 | 1 (nativa) | dot1q | R-LAN Gi0/1 (troncal: VLAN 10 y 20 etiquetadas) |
| 1 | 10 | access | PC-USER |
| 2 | 20 | access | PC-ADMIN |

Borrá los puertos que no se usan (3 a 7) para que nadie conecte algo por error a la VLAN 1.

### SW-DMZ

| Puerto | VLAN | Tipo | Conecta a |
| --- | --- | --- | --- |
| 0 | 1 | access | FGT-01 port3 |
| 1 | 1 | access | SRV-DMZ |

### Verificación

- En R-LAN: `show interfaces GigabitEthernet0/1.10` debe mostrar `Encapsulation 802.1Q Virtual LAN, Vlan ID 10`.
- Desde PC-USER, `ping 10.50.0.1`; desde PC-ADMIN, `ping 10.50.1.1`. Si uno falla, revisá que la VLAN del puerto de acceso coincida con la subinterfaz.

## Alternativa con IOSvL2 (si el profesor pide CLI en los switches)

Solo si se reemplaza el switch integrado por una imagen IOSvL2. Los puertos pasan a llamarse Gi0/0, Gi0/1 y Gi0/2.

```
! SW-LAN
hostname SW-LAN
no ip domain-lookup
vlan 10
 name USUARIOS
vlan 20
 name ADMIN
vlan 999
 name NATIVA-SIN-USO
!
interface GigabitEthernet0/0
 description Troncal hacia R-LAN Gi0/1
 switchport trunk encapsulation dot1q
 switchport mode trunk
 switchport trunk native vlan 999
 switchport trunk allowed vlan 10,20
 switchport nonegotiate
!
interface GigabitEthernet0/1
 description PC-USER
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
!
interface GigabitEthernet0/2
 description PC-ADMIN
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
!
interface range GigabitEthernet0/3, GigabitEthernet1/0 - 3
 shutdown
end
```

```
! SW-DMZ
hostname SW-DMZ
no ip domain-lookup
vlan 30
 name DMZ
!
interface range GigabitEthernet0/0 - 1
 switchport mode access
 switchport access vlan 30
 spanning-tree portfast
!
interface range GigabitEthernet0/2 - 3, GigabitEthernet1/0 - 3
 shutdown
end
```

Verificación: `show vlan brief` · `show interfaces trunk`.
