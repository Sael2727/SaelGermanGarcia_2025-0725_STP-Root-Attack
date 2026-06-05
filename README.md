# 👑 STP Claim Root Attack — Seguridad de Redes

<div align="center">

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![Scapy](https://img.shields.io/badge/Scapy-Latest-green?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Linux-orange?style=for-the-badge&logo=linux)
![License](https://img.shields.io/badge/Uso-Educativo-red?style=for-the-badge)

**Sael Germán García** | Matrícula: `2025-0725`  
Asignatura: Seguridad de Redes | Profesor: Jonathan Rondón  
Instituto Tecnológico de las Américas — ITLA | 2026

</div>

---

## 📋 Descripción del Ataque

El **STP Claim Root Attack** explota la ausencia de autenticación en el protocolo **Spanning Tree (IEEE 802.1D)**. Mediante la inyección de **BPDUs (Bridge Protocol Data Units) falsificadas** con una prioridad de puente de `0` — el valor más bajo posible — el atacante fuerza a todos los switches de la red a recalcular su árbol de expansión y a elegirlo como nuevo **Root Bridge (Puente Raíz)**, alterando los caminos de reenvío de tráfico de toda la infraestructura y posicionándose en una situación ideal para ejecutar ataques de interceptación.

> 💡 **Condición de vulnerabilidad:** El puerto del switch conectado al atacante (Et0/3) debe carecer de mecanismos de hardening STP como **BPDU Guard** o **Root Guard**.

---

## 🗺️ Topología de Red

### 📊 Segmentación de VLANs y Prioridades STP

| VLAN ID | Nombre | Prioridad STP Inicial | Estado |
|:-------:|:------:|:---------------------:|--------|
| 10 | Usuarios | 32778 (por defecto) | VLAN inalterada — Root SW1 |
| 20 | Servidores | 32788 (por defecto) | VLAN inalterada — Root SW1 |
| 99 | Gestión | 32867 (por defecto) | **VLAN objetivo** — atacante fuerza prioridad `0` |

### 📊 Matriz Analítica del Ataque (Estados de Spanning Tree)

| Fase | Root Bridge | Prioridad STP | Rol Puerto Et0/3 en SW1 |
|:----:|:-----------:|:-------------:|:-----------------------:|
| Antes del ataque | SW1 (Legítimo) | 32867 (32768 + ID 99) | Designated Port (Desg FWD) |
| Durante el ataque | Máquina Atacante | `0` (Cero) | Root Port (Root FWD) |
| MAC comprometida | `50:dc:15:00:2b:01` | — | Ubuntu se convierte en la raíz de VLAN 99 |

---

## ⚙️ Requisitos

```bash
# Sistema Operativo
Ubuntu Linux (recomendado)

# Dependencias
sudo apt update && sudo apt install -y python3-scapy python3-pip

# Privilegios requeridos
sudo / root
```

---

## 🔧 Configuración Previa

### Verificar estado inicial del STP en SW1
```cisco
SW1# show spanning-tree vlan 99
! Confirmar que SW1 es el Root Bridge con prioridad 32867
```

### Verificar que Et0/3 no tiene BPDU Guard ni Root Guard
```cisco
SW1# show spanning-tree interface ethernet0/3 detail
! El puerto debe operar como Designated FWD sin protecciones
```

---

## 🚀 Uso

```bash
# Ejecutar el ataque (por defecto: 100 BPDUs)
sudo python3 stp_root.py

# Especificar cantidad de BPDUs a enviar
sudo python3 stp_root.py 300

# Verificar el secuestro del Root Bridge en SW1
SW1# show spanning-tree vlan 99
# Resultado esperado: Root ID Priority 0 — Address 50dc.1500.2b01
```

---

## 🔬 ¿Cómo funciona?

| Paso | Componente | Descripción |
|:----:|:----------:|-------------|
| 1️⃣ | `ATTACKER_MAC` | Captura dinámicamente la MAC de `ens4` con `get_if_hwaddr()` — esta MAC se convierte en el nuevo Bridge ID |
| 2️⃣ | `build_bpdu()` | Ensambla manualmente la trama BPDU usando `struct` en formato Big-Endian (`!`), respetando el estándar IEEE 802.1D |
| 3️⃣ | Falsificación de prioridad | Inyecta `0x0000` (Prioridad **0**) en los campos `root_id` y `bridge_id` — matemáticamente el valor más bajo posible, garantizando ganar la elección |
| 4️⃣ | Encapsulación | Empaqueta la BPDU en cabecera LLC estándar y trama Ethernet hacia la dirección Multicast reservada de STP: `01:80:c2:00:00:00` |
| 5️⃣ | `stp_attack()` | Envía las BPDUs con `sendp()` en bucle cada **100ms** — 20× más frecuente que el Hello Time legítimo (2s), abrumando la topología y forzando reconvergencia |

### Estructura de la BPDU Falsificada

| Campo | Valor | Efecto |
|:-----:|:-----:|--------|
| Protocol ID | `0x0000` | STP estándar |
| BPDU Type | `0x00` | Configuration BPDU |
| Root ID Priority | `0x0000` | Prioridad **0** — gana cualquier elección |
| Root Path Cost | `0` | Costo mínimo al Root |
| Bridge ID | `0x0000` + MAC atacante | Se identifica como el nuevo puente |
| Hello Time | 2 seg | Estándar IEEE 802.1D |
| Max Age | 20 seg | Estándar IEEE 802.1D |
| Forward Delay | 15 seg | Estándar IEEE 802.1D |
| Destino Ethernet | `01:80:c2:00:00:00` | Multicast reservado STP |

---

## 🛡️ Contramedidas

### Opción A — Root Guard (puertos Designated hacia otros switches)
Bloquea temporalmente el puerto en estado `root-inconsistent` si recibe una BPDU superior, sin apagarlo.
```cisco
SW1# configure terminal
SW1(config)# interface ethernet0/3
SW1(config-if)# spanning-tree guard root
SW1(config-if)# end
```

### Opción B — BPDU Guard (puertos de acceso hacia usuarios finales)
Apaga el puerto inmediatamente (`err-disable`) ante cualquier BPDU recibido. Máxima protección perimetral.
```cisco
SW1# configure terminal
SW1(config)# interface ethernet0/3
SW1(config-if)# spanning-tree bpduguard enable
SW1(config-if)# end
SW1# write memory
```

> **¿Cuándo usar cada uno?**  
> `Root Guard` → puertos donde puede haber switches legítimos pero nunca un Root Bridge externo.  
> `BPDU Guard` → puertos de acceso (VPCs, usuarios) donde jamás debería llegar un BPDU.

---

## 📁 Archivos del Repositorio

| Archivo | Descripción |
|:-------:|-------------|
| [`stp_root.py`](stp_root.py) | Script principal del ataque |
| [`SaelGermanGarcia_2025-0725_Stp_Claim_Root_P1.pdf`](SaelGermanGarcia_2025-0725_Stp_Claim_Root_P1.pdf) | Documentación técnica completa |

---

## 🖼️ Capturas de Pantalla

- 📸 [Estado Inicial de la Topología STP](Capturas%20de%20Pantalla%20Stp%20Claim%20Root/Estado%20Inicial%20de%20la%20Topolog%C3%ADa%20STP.png)
- 📸 [Ejecución e Inyección de BPDUs Falsificados](Capturas%20de%20Pantalla%20Stp%20Claim%20Root/Ejecuci%C3%B3n%20e%20Inyecci%C3%B3n%20de%20BPDUs%20Falsificados.png)
- 📸 [Topología STP Comprometida (Secuestro del Root Bridge)](Capturas%20de%20Pantalla%20Stp%20Claim%20Root/Topolog%C3%ADa%20STP%20Comprometida%20(Secuestro%20del%20Root%20Bridge).png)
- 📸 [Activación de BPDU Guard (Cisco IOS)](Capturas%20de%20Pantalla%20Stp%20Claim%20Root/Activaci%C3%B3n%20de%20BPDU%20Guard%20(Cisco%20IOS).png)

---

## 📎 Recursos

📄 **Documentación Técnica:** [Ver Informe PDF](SaelGermanGarcia_2025-0725_Stp_Claim_Root_P1.pdf)  
▶️ **Video Demostración:** [Ver en YouTube](https://youtube.com/playlist?list=PLV_dKVnYXf6dpmk3j8uXPHAZdbrkCQGAY)

---

## 📚 Referencias

1. Cisco Systems. *Spanning Tree Protocol Configuration Guide*. Documentación oficial de Cisco IOS.
2. Scapy Project. *Scapy: Interactive packet manipulation program*. [https://scapy.net/](https://scapy.net/)
3. IEEE. *IEEE 802.1D — MAC Bridges and Virtual Bridged Local Area Networks*. Estándar base de STP.
4. Reconocimiento especial: Troubleshooting, base del script y documentación apoyado en Inteligencia Artificial.

---

<div align="center">

⚠️ **AVISO LEGAL** ⚠️  
*Este script fue desarrollado exclusivamente con fines académicos y educativos.*  
*Su uso en redes sin autorización explícita es ilegal y éticamente inaceptable.*

</div>
